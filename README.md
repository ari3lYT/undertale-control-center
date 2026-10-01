# Undertale Control Center

[Русская версия](README.ru.md)

A local, browser-based save editor, timeline, diagnostics dashboard, and optional live bridge for the Steam Linux version of **UNDERTALE**.

The application runs only on `127.0.0.1`. It automatically discovers the active Steam installation and the save directory derived from the GameMaker build name, keeps coupled files consistent, creates recovery snapshots, and explains changes in plain language.

## Features

- structured editor for `file0`, `file9`, `undertale.ini`, `config.ini`, genocide markers, and other files the game may create;
- linked writes for values that UNDERTALE normally updates together, with validation and conflict previews;
- inventory, phone, room, plot, FUN, bonus/version, and all 512 global flag references;
- save slots, presets, clean-run reset, automatic backups, semantic history, diffs, and rollback;
- runtime dashboard, plot split timer, save-field memory log, and input log when the optional game bridge is installed;
- live flag/FUN changes and live bundle loading outside battles and dialogs when supported by the bridge;
- manager settings for WASD, Z/X/C aliases, debug controls, logging, and polling;
- no third-party Python packages and no cloud service.

## Requirements

- Linux;
- Python 3.10 or newer;
- a legally owned Steam copy of UNDERTALE.

Disk editing and backup features work without patching the game. Live memory features, the runtime log, WASD/ZXC toggles, and hot loading require the optional bridge described in [`game-module/README.md`](game-module/README.md).

## Quick start

### Ready-to-run Linux packages

Download the latest files from [GitHub Releases](https://github.com/ari3lYT/undertale-control-center/releases/latest):

- `undertale-control-center_VERSION_amd64.deb` — install on Debian, Ubuntu, Mint, and compatible distributions, then launch **Undertale Control Center** from the application menu;
- `undertale-control-center-vVERSION-linux-x86_64.tar.gz` — portable build: extract it and run `./undertale-control-center`.

The packaged application includes Python and all application files. It does not include UNDERTALE or a patched `game.unx`.

### Run from source

```bash
git clone https://github.com/ari3lYT/undertale-control-center.git
cd undertale-control-center
./start.sh
```

The browser opens at <http://127.0.0.1:8765>. To suppress automatic browser launch:

```bash
python3 server.py --no-browser
```

Run the tests with:

```bash
python3 -m unittest discover -v
```

## Safety model

- The service binds to loopback only and rejects browser write requests from non-local origins.
- Every manager write is preceded by a recovery snapshot.
- A preview hash prevents committing against files that changed after validation.
- `file0`, `file9`, and INI summaries are updated as a bundle unless independent mode is explicitly selected.
- Live commands are session-bound, expire after 30 seconds, and wait for a safe exploration state.
- Arbitrary combinations of plot and flags can still describe a state that never occurs naturally. Read the conflict preview and keep Steam Cloud in mind.

Application state, slots, and history are stored in `~/.local/share/undertale-control-center`. Game saves are discovered under the active build's directory in `~/.config`.

## Supported scope

This release targets the native Linux GameMaker build distributed through Steam, including the current anniversary build and bonus variants exposed by that build. Windows and macOS discovery are not implemented.

The interface can be switched between English and Russian with the `RU / EN` control in the top bar, and the choice is remembered by the browser. Detailed flag, room, and plot annotations extracted from an installed localized build may retain that build's language.

## Legal

This is an unofficial fan tool and is not affiliated with Toby Fox, 8-4, or Valve. No game executable, `game.unx`, music, sprites, dialogue dump, or other commercial game asset is included. The optional bridge is source-only and must be applied to the user's own copy.

Project code is available under the [MIT License](LICENSE). UNDERTALE and all game assets remain the property of their respective owners.
