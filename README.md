# Datakin Level Workshop — ROM edition

A small, local level editor for **Datakin: Server Delver**. Supply your own
supported ROM, edit its stages in your browser, and export a separate playable
ROM. The editor needs **Python 3.10 or newer** and a modern browser. It uses only
Python's standard library: no pip packages, compiler, account, or connection to
an online service is needed to run it.

**No game ROM, game engine source, artwork, music, reference material, player
saves, or emulator is included.** This edits Datakin's level format; it is not
a general editor for arbitrary GBA games.

**[Download the editor ZIP](https://github.com/Sunspark22/datakin-level-workshop/releases/latest/download/Datakin-Level-Workshop.zip)**
· **[Get the game on itch.io](https://circuitfoxes.itch.io/datakin-server-delver)**

The ZIP is the ready-to-run Python/browser edition, with its full source code.
It is not a compiled Windows executable; install Python before launching it.

## Start

1. Download and extract the whole editor ZIP somewhere you can write files,
   such as Documents. Install [Python 3.10 or newer](https://www.python.org/downloads/)
   if it is not already installed.
2. Put your original ROM at **`rom/Datakin-Server-Delver.gba`**.
3. On Windows, double-click **`Start Editor.cmd`**. Keep its console open while
   editing. On macOS/Linux, run **`python3 server.py --open`** in this folder.
4. Your browser opens the local workshop, normally at `http://127.0.0.1:8776`.
   If the ROM is missing or unsupported, the setup page explains what is needed.
5. When finished, use **How to use → Quit editor**, or close the console.

This release supports these exact original builds (the latest is recommended):

| Build | File size | SHA-256 |
| --- | ---: | --- |
| v0.79, revision 79 | 30,929,624 bytes | `78a2b42fe93a42dc43e5a0707cb01548d143edb55dad4d84b5d5825782b3a9a4` |
| v0.78, revision 78 | 30,929,496 bytes | `7f8f5efe7da5bdeba40a60c4b21c767ffb896fc228c5bf2895f7dc7c3237c79b` |

Both have 17 editable stage slots: Training, ten resonance stages, and six
Gauntlet parts. The title screen does not show a version; the file hash identifies it.

The editor checks the full file hash, not just its filename. Older releases,
modified exports, padded cartridge dumps, and other games are rejected. Keep
the original in `rom`; do not replace it with a workshop export. Future game
builds need a verified matching profile. Use a separate extracted editor folder
for each ROM version; saved workspace layouts are tied to their input ROM.

### Future ROM builds

If the setup page says your original ROM is unsupported, click **Check for ROM
support**. It looks for a matching compatibility profile in this repository and
installs it only after checking the exact ROM hash, bounded offsets, and every
stage's byte-exact round-trip. The check downloads JSON metadata only; it never
uploads your ROM or layouts, or downloads executable code. Editing stays offline.

New game releases need a maintainer to publish their verified profile first.
A build that changes the level format or adds editor features may also need a
new editor release. An unknown build is refused safely, rather than patched
using an older build's offsets. The README table lists bundled profiles; the
[support catalog](profiles/index.json) may contain newer ones.

## Make an edit

- Choose a stage. Select an object to move/resize it or edit its properties.
- Choose **Enemy**, then an **Enemy type**, to add a foe. Each foe has its own
  health value. The preview shows layout shapes and labels, not game artwork.
- Platform properties include slippery, disappearing, cloud, raft, and boss
  floor flags. Moving platforms expose travel, timing, and direction.
- **Stage settings** lets you add space above/below or insert a horizontal
  section. Insertion shifts the objects to the right and stretches crossing
  ground; it also consumes an inserted-section record in the ROM.
- **Save draft** saves a dated copy. It does not apply the stage to other builds.
- **Apply to workspace** makes the stage part of future exports from this
  editor folder and backs up the previous layout in the draft list. Repeat for
  every stage you want included. It does **not** overwrite your input ROM.
- **Build edited ROM** combines every applied stage with the draft currently
  open. Unchanged slots come directly from the supplied original ROM.
- Download the result, or find it at **`output/Datakin-Edited.gba`**. Each build
  replaces that output, rather than creating more numbered game versions.
  Close it in your emulator before rebuilding if Windows says it is in use.
- Open the output in your own emulator, or copy it to your GBA/Pocket setup.
  Use a separate test save: an existing save can retain collected items or old
  checkpoints. The workshop never opens or writes player save files.

Use **Export JSON** to share a layout without sharing the whole game ROM.
**Import JSON** reads those layouts, including drafts from the original
developer workshop. An oversized imported design can be saved/exported as a
draft, but must fit the supplied ROM before it can be applied or built.

## What this edition can change

Platforms, movers, slopes, hazards, enemies and their health, pickups, caches,
checkpoints, stage size/name, water/current areas, grass, vines, spotlights,
switches, and existing entrance/exit markers are editable. Hidden-byte identity
stays tied to the stage slot. The stage's environment is fixed to keep its
existing boss, palettes, music, and scripted events consistent.

This edition does not create new enemy behaviors, bosses, music, artwork,
special road/flight encounters, stage slots, or hub doors. Miniboss markers
move the entrances/return points of encounters already in the ROM; they don't
create a new encounter. Some theme events are scripted rather than level data.
Check the result in the game after making large structural changes.

## Fixed ROM storage

Unlike the developer editor, this edition patches an existing cartridge instead
of recompiling the engine. It **cannot grow the engine's RAM arrays**. The
inspector shows each collection's used/available count; **Check layout** also
checks these limits. Oversized builds are refused before any output is replaced.

For the supported ROM, some examples are:

| Collection | Maximum per stage |
| --- | ---: |
| Static platforms | 66 |
| Moving platforms | 37 |
| Static + moving combined | 78 |
| Placed enemies | 32–42, depending on reserved summon slots |
| Moving spikes | 12 |
| Disappearing platforms | 24 |
| Clouds | 8 |
| Checkpoints | 6 |
| Bit caches | 3 |
| Inserted-section records | 1 |

Water and Gauntlet reserve two enemy slots; any stage with spotlights reserves
eight more. Other exact limits appear in the inspector. Increasing stage width
or height does not increase these counts, but populated areas can still affect
GBA performance. The normal coordinate, movement, index, and timing checks also
apply. Keep maps within 8000 × 2048 pixels.

## Where files go

```text
rom/Datakin-Server-Delver.gba    Your original game (read only)
workspace/drafts/                Dated drafts and automatic before-apply backups
workspace/applied/               Stages included in future exports
output/Datakin-Edited.gba        The latest playable export
profiles/datakin-v0*.json        Hashes, offsets, and storage layout; no game data
web/                            Browser editor
rom.py, validation.py, server.py ROM patcher, validation, and local server
```

To undo an applied layout, open its **Backup before apply** draft and apply it
again. To start entirely fresh, stop the editor and move `workspace` somewhere
else as a backup; reopening uses the original ROM again. Browser recovery keeps
one unfinished layout, so decline restoration if you want a clean start.

The server listens only on your own computer. It serves an explicit file list,
requires a session token for changes, and never exposes the input ROM as a
download. It does not upload layouts or ROMs. Do not use it as a public web server.

## For developers

`python server.py --check-rom` checks the supplied file and all 17 binary
round-trips without starting a server. `python -m unittest discover -s tests`
runs patching, storage, workspace, and HTTP checks. ROM-dependent tests skip if
no compatible ROM is supplied. `node tests/model.mjs` runs optional editor-model
checks; Node is not required to use the workshop.

Set `DATAKIN_TEST_ROM` to the absolute path of a supported original ROM to run
the full local tests without copying the game into the repository. Public CI
runs only the checks that need no ROM. `python build_release.py` produces
`dist/Datakin-Level-Workshop.zip` from an explicit source-file allowlist, with
a SHA-256 manifest; personal files are never included by that packager.

New names are appended as bounded strings. Level records are patched in place.
Game executable code and artwork/music bytes stay unchanged; no-edit exports
are byte-identical to the supplied ROM. All writes go to workspace/output.

The profile is specific to the game's compiled structure. Changing a checksum
to accept another build is unsafe: its offsets and capacities must be verified,
including a byte-identical round-trip and gameplay check, by a maintainer.

## License

The editor code and documentation in this repository are available under the
[MIT license](LICENSE). The separately supplied Datakin game, engine, characters,
artwork, music, and other game assets are not included and are not covered by
this license. Exported ROMs still contain the game's content; share your layout
JSON files when sharing your own level designs.
