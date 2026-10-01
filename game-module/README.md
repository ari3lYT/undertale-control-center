# Optional game bridge

These are source patches for UndertaleModTool/UndertaleModCli. They add the local `ucc-events.log`, short-lived command files, save-field monitoring, native WASD/ZXC aliases, runtime settings, and safe-state live loading used by the manager.

No patched game file is distributed. Build only from a game copy you legally own.

## Build

1. Download a compatible Linux `UndertaleModCli` release from the official [UndertaleModTool repository](https://github.com/UnderminersTeam/UndertaleModTool).
2. Verify/repair UNDERTALE in Steam if your current `game.unx` already contains an older version of this bridge.
3. Close the game and run this command from the repository root:

```bash
./game-module/build.sh \
  /path/to/UndertaleModCli \
  ~/.local/share/Steam/steamapps/common/Undertale/assets/game.unx \
  /tmp/ucc-game.unx
```

4. Keep a backup of the original file, then replace the installed `assets/game.unx` with the generated `/tmp/ucc-game.unx`.
5. Start the manager and the game. The Devtools page should report that the module is connected.

The scripts are intentionally applied in numeric order. Each script checks important code anchors and refuses to continue when the target build no longer matches the expected GameMaker code. Never force a failed patch onto another game version.

## Runtime files

- `ucc-events.log` — plot transitions, selected save-field changes, module status, and optional input transitions;
- `ucc-settings.ini` — manager-controlled WASD/ZXC/debug/logging settings;
- `ucc-command.ini` plus staging files — a session-bound, expiring live request.

All files are created in the active GameMaker save directory. The manager validates the module session token and creates a recovery slot before live bundle operations.

