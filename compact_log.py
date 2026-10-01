"""One-time compaction of legacy runtime noise; preserves save-related events.

When Undertale is running, pause only its runner while atomically replacing the
log, so an append cannot race the rewrite. The caller supplies a backup path.
"""
import argparse
import json
import os
import shutil
import signal
import tempfile
from collections import Counter
from pathlib import Path

from runtime import is_save_memory_key


def retain(lines):
    counts = Counter()
    last_settings = None
    last_heartbeat = None
    last_heartbeat_wall = -1e30
    for line in lines:
        parts = line.rstrip(b'\r\n').split(b'|')
        kind = parts[0]
        if kind == b'E':
            last_settings = None
            last_heartbeat = None
            last_heartbeat_wall = -1e30
        if kind in (b'V', b'D') and len(parts) >= 4:
            from urllib.parse import unquote
            key = unquote(parts[3].decode('utf-8', errors='replace'))
            if not is_save_memory_key(key):
                counts['discarded_memory_noise'] += 1
                continue
        elif kind == b'Q' and len(parts) >= 7:
            settings = tuple(parts[3:])
            if settings == last_settings:
                counts['discarded_unchanged_settings'] += 1
                continue
            last_settings = settings
        elif kind == b'H' and len(parts) >= 7:
            try:
                wall = float(parts[1])
            except ValueError:
                wall = last_heartbeat_wall + 2000
            state = tuple(parts[3:])
            if state == last_heartbeat and wall - last_heartbeat_wall < 2000:
                counts['discarded_redundant_heartbeat'] += 1
                continue
            last_heartbeat = state
            last_heartbeat_wall = wall
        counts['retained'] += 1
        yield line
    return counts


def compact(path, backup, pid=None):
    path = Path(path).resolve()
    backup = Path(backup).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if backup.exists() or backup == path:
        raise FileExistsError(backup)
    if pid is not None:
        executable = os.readlink(f'/proc/{pid}/exe')
        if Path(executable).name != 'runner' or 'Undertale' not in executable:
            raise ValueError('PID does not identify the Undertale runner')
    paused = False
    temporary = None
    try:
        if pid is not None:
            os.kill(pid, signal.SIGSTOP)
            paused = True
        shutil.copy2(path, backup)
        before = path.stat().st_size
        counts = Counter()
        descriptor, temporary = tempfile.mkstemp(prefix='ucc-clean-', dir=path.parent)
        with path.open('rb') as source, os.fdopen(descriptor, 'wb') as target:
            iterator = retain(source)
            while True:
                try:
                    target.write(next(iterator))
                except StopIteration as done:
                    counts.update(done.value or {})
                    break
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
        temporary = None
        return {'before_bytes': before, 'after_bytes': path.stat().st_size,
                'backup': str(backup), **counts}
    finally:
        if temporary is not None:
            os.unlink(temporary)
        if paused:
            os.kill(pid, signal.SIGCONT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('log', type=Path)
    parser.add_argument('backup', type=Path)
    parser.add_argument('--pause-pid', type=int)
    args = parser.parse_args()
    print(json.dumps(compact(args.log, args.backup, args.pause_pid), ensure_ascii=False))
