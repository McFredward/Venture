# Steam Frame passthrough test branch

This branch is exactly the passthrough PR plus the independently reviewed Windows
build/install scripts. No launcher idle/pacing, Unity fragment, preview packaging,
FFmpeg discovery or global identity-scanner changes are merged here.

Installation uses the general script defaults: the native Program Files directory
(normally `C:\Program Files\Venture`) and a **Venture** desktop shortcut.
Application sources are identical to `feat/steam-link-passthrough`.

## Install and update on Windows

From the existing clone, close Venture and its game, then run:

```powershell
git fetch origin
git switch test/steam-frame-passthrough
git pull --ff-only
.\install.cmd
```

For later updates on this branch, `git pull --ff-only` and `install.cmd` are enough.
Changes from the PR branch are merged into this test branch, preserving its update
history. The first build is expensive; subsequent runs reuse dependency/compiler
caches and compile changed code. One installation directory is overwritten; no
revision-specific installation directories or backup copies are retained.
The final file installation requests Windows administrator approval when needed;
compilation and application startup stay in the original user's process.

Build logs are in `build/local-install/*-build.log`. Temporary package copies are
removed even when a build/install fails. The script's general options and repair
behavior are documented in [LOCAL_BUILD.md](LOCAL_BUILD.md).

Use the existing separately installed
[Steam Link Native Passthrough](https://github.com/McFredward/steam-link-native-passthrough)
PC/Frame companions and enable **Settings → Runtime → Passthrough (mixed reality)**.
The Steam Link backend remains Steam Frame only; native host passthrough is also
behind this default-off setting. The build/install script does not change the Frame,
SteamVR or companion installation. The launcher sets `VENTURE_PASSTHROUGH=1` or `0` for each game; users do not
need to set it themselves.

This test branch includes current upstream main (`ae3ed1f`) and the November 3
review fixes from the rebased passthrough PR. Its application sources and
passthrough tests are identical to that PR branch.

## Hardware checks after the review changes

- With passthrough off, confirm the game uses ordinary VR even on a host that
  exposes native passthrough. Enable the option and relaunch for MR.
- Start Spirit Sling Tabletop in MR; inspect both eyes, fractional transparency
  and additive effects.
- Toggle between MR and ordinary VR repeatedly in the same session.
- Exercise headset sleep/session stop and resume. A stopped run must not request
  cameras again from its last frame; a successfully restarted run can re-enable MR.
- Open and close Steam overlays and return to the game.
- Record the installed Venture revision, companion versions, game version and
  matching Venture/PC/Frame logs with any failure report.

Software tests cover actual guest frame/session paths, ordinary VR depth/MSAA/
float formats and async ownership, byte-identical ordinary shaders, real Vulkan
pixels and the production Windows pipe client. They are not a new headset result.

## Independent PR branches

| Branch | Scope |
| --- | --- |
| `feat/steam-link-passthrough` | PR #34, passthrough and its tests |
| `feat/windows-build-install` | General compile/package/install scripts |
| `feat/launcher-idle` | Idle CPU and event/frame pacing |
| `fix/unity-fragment-permissions` | Remaining headless fragment API/synchronization |
| `feat/preview-packaging` | Optional Python preview deployment and legacy cleanup |
| `fix/windows-ffmpeg-verifier` | GnuPG discovery and MSYS verifier paths |
| `fix/package-public-project-urls` | Public project URLs in shipping identity scans |

Only the first two are combined in this test branch. Every topic branch starts
from upstream main and contains its own relevant tests/CI. No new upstream PRs
are created automatically; these branches are ready for separate submissions.
