# Steam Frame passthrough test branch

This branch follows upstream Venture, including the 0.2 mixed-reality backends,
and retains the independent Windows build/install scripts. PR #34 was merged
upstream; its old feature branch is no longer the source of application updates.

The November 8 update includes upstream `4f9fcd2`. The runtime adds diagnostic
messages for the temporary SBN1 companion connection: probe versus active
connection, client/server process IDs, waiting versus granted RGBA source
permission, and each prepared eye's image format, extent, rectangle and FOV.
This is a diagnostic build, not a confirmed fix for the reported
black background on Steam Frame. The permission checks and image submission
remain unchanged.

## Install and update on Windows

From the existing clone, close Venture and its game, then run:

```powershell
git fetch origin
git switch test/steam-frame-passthrough
git pull --ff-only
.\install.cmd
```

For later updates, `git pull --ff-only` and `install.cmd` are enough. Updates
preserve this branch's history. Installation updates the same Program Files
directory, normally `C:\Program Files\Venture`, and the **Venture** desktop
shortcut. The final installation requests administrator approval when needed;
compilation and startup stay in the original user's process.

Build logs are in `build/local-install/*-build.log`. See
[LOCAL_BUILD.md](LOCAL_BUILD.md) for script options and repair behavior.

## Steam Frame setup and current investigation

Use the separately installed
[Steam Link Native Passthrough](https://github.com/McFredward/steam-link-native-passthrough)
PC/Frame companions. Enable **Settings → Runtime → Passthrough (mixed reality)**
and relaunch the game. Upstream 0.2 enables passthrough by default, and Venture
chooses an available backend. Frame through Steam Link uses the external source
backend; a runtime offering native passthrough can use that instead. The install
script does not update SteamVR or either companion component.

In the reported November 8 run, Spirit Sling initialized passthrough and Venture
selected the external source. The companion answered SBN1 v2, but Venture never
received RGBA source permission and therefore submitted opaque images. SteamVR
reported successful frame submission. Its dashboard was closed during the
failure. These logs establish the missing permission, not which update caused it.

The same installation runs Demeo successfully. The room-scan agent also verified
that the roomscan.17 package's PC provider DLL is byte-identical to stable main.
This narrows the investigation but does not identify a Venture regression.

The companion's `no-declaration` counter in those logs names the compositor
process. It must not be treated as proof that Venture sent an invalid request.
A local protocol comparison confirmed byte-identical v1/v2 requests with the
previous implementation and compatible replies from the current companion.

For the next hardware run, retain the matching Venture runtime, `vrserver`, and
`vrcompositor` logs. The new `active connection` message identifies both ends;
`has not granted RGBA source permission` distinguishes a valid waiting reply
from `granted RGBA source permission`. A grant alone is not proof that a camera
image reached the headset.

An old, previously working Venture build tested with the same game, SteamVR,
companion versions and settings is the useful comparison. Record those versions
and the Venture revision for each run. Local protocol tests cannot substitute
for that headset comparison.
