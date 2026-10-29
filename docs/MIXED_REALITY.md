# Experimental mixed reality over Steam Link

This branch connects Quest OpenXR passthrough to
[Steam Link Native Passthrough](https://github.com/McFredward/steam-link-native-passthrough).
It targets **Quest games emulated on a Windows PC and displayed on Steam Frame**.
The Frame supplies its own camera image; camera video never enters Venture.

**Spirit Sling Tabletop is the requested first hardware reference, not a
verified compatibility result.** Software GPU checks and Windows compilation
do not establish an end-to-end Spirit Sling/Steam Link/Frame result.
It must remain experimental until that validation succeeds.
It does not establish full support for every Quest MR feature or game.

## Trying the integration

On your Windows PC, select the fork branch once:

```powershell
git fetch origin
git switch feat/steam-link-passthrough
```

For each test update, pull and run the installer from the checkout:

```powershell
git pull --ff-only
.\install-passthrough.cmd
```

It prepares the project's pinned build dependencies, compiles the current
checkout, runs the OpenXR metadata/Unity permission checks, packages Venture
and installs a verified portable build directly in
`%LOCALAPPDATA%\Venture-Passthrough`. Updates overwrite that same installation;
previous builds are not retained. The next installation also removes the older
installer-created builds from its `versions` subdirectory before copying files,
freeing their disk space for the update.
The `Venture Passthrough` desktop shortcut starts the build with the experimental
setting; it uses the normal Venture game library. Close Venture and its game
before running the installer.

Use an ordinary Windows terminal. Git for Windows is required; Python 3.13+
x64 is reused or installed for the current user through WinGet when available.
FFmpeg verification discovers Git's bundled `gpg`/`gpgv` even when only Git's
`cmd` directory is on PATH, and also recognizes native GnuPG installations.
The first build downloads and compiles portable toolchain, JDK, FFmpeg and
ANGLE dependencies and can take substantially longer than later cached builds.
The installer keeps its build log under `build/passthrough-install`.
Build subprocess stdout and stderr are explicitly forwarded into that
transcript, including Python tracebacks on Windows PowerShell 5.1.

PowerShell options, when needed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-passthrough.ps1 -Jobs 4 -NoLaunch
```

`-InstallDir` selects a separate preview root. Files are checked and replaced
individually, using at most one temporary file instead of staging a second full
build. Unchanged files are reused and obsolete packaged files are removed.
If an update is interrupted, rerun the installer to repair it. The normal
Venture installation, shared game library and build caches are retained.

1. Build this branch using the normal [Windows build instructions](../README.md#build-windows).
2. Install matching PC and Frame companions using the linked project's normal
   installer. Its supported host route requires Windows x64, NVIDIA, HEVC and
   Steam Frame over Steam Link. This patch does not install or modify companions.
3. Select SteamVR as the active OpenXR runtime and start the Steam Link session.
4. Close Venture, then use the packaged `venture-passthrough.cmd` or start it
   from PowerShell with the experimental setting:

   ```powershell
   $env:VENTURE_STEAM_LINK_PASSTHROUGH = '1'
   & '.\venture.exe'
   ```

5. Launch the Quest build of Spirit Sling Tabletop and enable its MR mode.
   The first submitted pair remains opaque until the companion grants the
   source format. The runtime log reports waiting, acceptance and withdrawal.
   A format grant alone does not prove a correct headset picture.

Game logs use the shared `%LOCALAPPDATA%\Venture\logs` directory, even when the
preview executable is installed under `Venture-Passthrough`. For Spirit
Sling, collect `runtime-com.meta.spiritsling.log`, its `.console.log` counterpart
and `launcher.log` after the test. A correctly enabled Steam Link backend logs
`Create passthrough: backend=Steam Link` when the game creates its feature.

Remove the environment variable and restart Venture to disable the experimental
Steam Link backend. Hosts offering native `XR_FB_passthrough` use their own
implementation without this setting. A32 guests do not expose these APIs yet.

## Implemented boundary

| Area | Behavior |
| --- | --- |
| Guest API | A64 `XR_FB_passthrough`, properties, handles, create/destroy, start/pause, layer resume/pause and reconstruction opacity |
| Native host | Passthrough calls and layers are forwarded; native triangle meshes and geometry instances are available when the host offers them |
| Steam Link source | SBN1 v2 with bandwidth accounting; fresh v1 connection/nonce fallback for an older endpoint |
| Identity | Canonical local runtime from `openvrpaths.vrpath`, bounded process discovery, nonredirected executable paths, held process lifetime, kernel pipe server PID and actual Venture process PID |
| Wire validation | Version, size, flags, profile, PIDs, echoed nonce, nonzero binding/generation and zero reserved bytes |
| Connection | One worker and one live pipe; bounded initial/partial-record waits; healthy idle leases have no periodic expiry; EOF, malformed replies, process death and opt-out revoke permission |
| Color/coverage | One reconstruction underlay followed by one stereo projection, or a camera-only reconstruction layer |
| Stereo | Actual released image and array slice copied to independent 2D host textures; original poses, FOV, rectangles, resolution and source pixels are preserved |
| Alpha | Fractional coverage and premultiplied additive emission preserved; straight alpha premultiplied once; opaque layers and unavailable grants produce A=1 |
| Opacity | Camera opacity P with a projection uses A'=1-P*(1-A), retaining scene RGB contribution E |
| Lifecycle | Pause, layer removal, session stopping/loss/end and destruction withdraw source intent; current single-projection VR output remains opaque on MR exit |

The Steam Link path currently accepts single-sample 8-bit RGBA/BGRA UNORM or
sRGB color swapchains, including arrays. It uses Venture's existing host format
fallback and value conversion where SteamVR requires another supported format.
The guest image-layout vertical flip is applied to pixels and submitted rects.
The companion owns native reprojection, foveation, exact encoded-video/mask
association, camera permission and recovery. Venture supplies no guessed frame
numbers, separate mask stream or color-key extraction.

Unsupported Steam Link arrangements return errors: additional composition
layers, projected passthrough geometry, camera color maps/edge effects,
camera-only partial opacity, multisampled or HDR exchange images, and enabled
composition color transforms. Depth and motion chains are not forwarded through
the ordinary-RGBA route. This patch does not implement room/scene understanding,
spatial anchors, environment-depth occlusion, camera texture access or private
VrApi passthrough interfaces. Games requiring these need additional work.

## Validation

The focused fixture builds production lifecycle/chain/stereo/copy/shader code
against a scripted OpenXR host and source connection, with real Vulkan GPU
images and pixel readback. Its transport is scripted: it does not execute
Windows named-pipe discovery, the SteamVR Vulkan-to-native copy, encoding,
streaming or Frame composition.

On a Linux development host with CMake, a C++23 compiler, Vulkan development
headers/loader, a Vulkan driver and `glslangValidator`:

```sh
cmake -S tests/passthrough -B build/passthrough-tests -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build/passthrough-tests --parallel 2
ctest --test-dir build/passthrough-tests --output-on-failure
```

The fixture checks SBN1 positive/negative/malformed records, native forwarding,
capability filtering, null passthrough spaces, lifecycle, actual stereo slice
separation, UNORM/sRGB pixel preservation, straight/fractional/additive alpha,
opacity, unavailable/revoked grants, MR-to-VR transitions and unsupported layouts.
Registry regeneration is checked too. The dedicated workflow runs these tests
on Mesa's software Vulkan driver on forks as well as upstream PRs.
Its Windows job also compiles the affected production XR sources with the
project's pinned LLVM-MinGW/libc++ toolchain and `VK_NO_PROTOTYPES`, without
requiring a headset or rebuilding ANGLE. String-literal pointer comparisons
are compile errors in that check.

The supplied Spirit Sling 1.2.0/version-code 24 baseline report shows both a
missing `XR_FB_passthrough` extension with Insight Passthrough initialization
failure and Unity permission-helper calls rejected by the framework's fragment
thread checks. The Java fix allows background lookups and queued commits as in
AOSP 12L, while lifecycle execution and `commitNow` still require the UI Looper.
`framework_fragment_permissions` tests that actual callback path. These are
identified baseline defects, not proof that every cause of the black picture
has been removed.

For the Spirit Sling hardware result, record the exact game version, Venture
revision, PC/Frame companion versions, SteamVR versions, GPU/driver and bitrate.
Retain matching PC/Frame logs and observe:

- First launch, intro/loading, table placement, gameplay and in-game MR toggle.
- Both eyes independently, solid objects, soft edges, particles, UI and fades.
- Steam overlay and interactive desktop, then return to the game.
- Companion absence, connection loss/reconnect, standby/resume and clean exit.
- Whether the game requests any currently unsupported layer or spatial API.

Compare with ordinary VR at the same render settings. Only an observed paired
headset result establishes that SteamVR and the companions preserve Venture's
final coverage for this game's actual render layout.

For a black picture with working audio/controllers, collect a runtime debug
report first. Check the `Guest requests XR_FB_passthrough` and
`Create passthrough` messages, then `Steam Link frame refused`/`Eye unavailable`
and source waiting/acceptance. `VENTURE_TRACE_XR_FRAMES=1` adds bounded early
frame layer-type/flag logs. Audio or controller models alone do not establish
that the game submitted a valid color projection or requested passthrough.

The current application-source contract is documented in the companion's
[SBN1 API](https://github.com/McFredward/steam-link-native-passthrough/blob/main/docs/protocols/application-source-v1.md)
and [integration guide](https://github.com/McFredward/steam-link-native-passthrough/blob/main/docs/development/GAME-INTEGRATION.md).
