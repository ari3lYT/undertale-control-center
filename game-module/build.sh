#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 /path/to/UndertaleModCli /path/to/input/game.unx /path/to/output/game.unx" >&2
  exit 2
fi

tool="$(realpath "$1")"
input="$(realpath "$2")"
output="$(realpath -m "$3")"
root="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "$input" == "$output" ]]; then
  echo "Refusing to overwrite the source game file. Choose a separate output path." >&2
  exit 2
fi

if [[ ! -x "$tool" || ! -f "$input" ]]; then
  echo "UndertaleModCli must be executable and the input game.unx must exist." >&2
  exit 2
fi

cd "$root"
"$tool" load "$input" --output "$output" --overwrite \
  --scripts game-module/01-ControlCenterBridge.csx \
  --scripts game-module/02-RuntimeSettings.csx \
  --scripts game-module/03-NativeInput.csx \
  --scripts game-module/04-MonitorV6.csx \
  --scripts game-module/05-LiveBundle.csx \
  --scripts game-module/06-SaveFieldsMonitor.csx \
  --scripts game-module/07-QuietRuntime.csx

echo "Built: $output"
echo "Back up the installed game.unx and close UNDERTALE before replacing it."
