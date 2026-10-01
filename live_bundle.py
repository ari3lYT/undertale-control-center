"""Stage-only transport. Game performs the transaction between its own events."""
import configparser
import hashlib
import io
import os
import time
from pathlib import Path
from bundles import GAME_FILES, read_bundle, digest


def prepare(root, after, expected, wall_ms, token, load_file=None):
    root=Path(root)
    before=read_bundle(root)
    if digest(before)!=expected: raise ValueError('Файлы изменились: обнови план live-применения.')
    if set(after)!=set(GAME_FILES): raise ValueError('Неполный набор live-файлов')
    if load_file not in (None,'file0','file9'): raise ValueError('Неподдерживаемый источник live-загрузки')
    if load_file and after[load_file] is None: raise ValueError('Нет сейва для загрузки в память')
    if (root/'ucc-live-request.ini').exists(): raise ValueError('Предыдущая live-команда ещё ожидает ответа игры')
    seq=time.time_ns()//1_000_000
    stage=root/f'ucc-stage-{seq}';stage.mkdir()
    manifest=configparser.ConfigParser(interpolation=None)
    manifest['command']={'seq':str(seq),'expires':str(int(wall_ms)+30000),'token':str(token),
        'load_file':load_file or '', 'count':str(len(GAME_FILES))}
    for i,name in enumerate(GAME_FILES):
        row={'name':name}
        for label,bundle in (('before',before),('after',after)):
            raw=bundle[name]
            row[label]='absent' if raw is None else hashlib.md5(raw).hexdigest()
            if raw is not None:
                with (stage/f'{label}-{name}').open('xb') as f:
                    f.write(raw);f.flush();os.fsync(f.fileno())
        manifest[str(i)]=row
    out=io.StringIO();manifest.write(out)
    tmp=root/'ucc-live-request.ini.tmp';tmp.write_text(out.getvalue(),encoding='utf-8')
    os.replace(tmp,root/'ucc-live-request.ini')
    return {'ok':True,'queued':True,'seq':seq,'files':[n for n in GAME_FILES if before[n]!=after[n]],
        'message':'Команда подготовлена. Игра проверит исходные файлы и применит её вне боя и диалога.'}


def status(root):
    p=Path(root)/'ucc-live-result.ini'
    if not p.exists(): return {'state':'none'}
    c=configparser.ConfigParser(interpolation=None)
    try:
        c.read(p,encoding='utf-8')
        result={k:v.strip('"') for k,v in c['result'].items()}
        if 'seq' in result: result['seq']=str(int(float(result['seq'])))
        return result
    except (OSError,ValueError,KeyError,configparser.Error): return {'state':'unreadable'}
