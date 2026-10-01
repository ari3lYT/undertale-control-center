"""Read-only discovery of native Linux Undertale and its GameMaker save prefix.

GEN8 layout follows UndertaleModLib.Models.UndertaleGeneralInfo.Serialize.
No folder is selected merely because its save files have a recent timestamp.
"""
import os
import re
import struct
from pathlib import Path


def game_name(data):
    with Path(data).open('rb') as f:
        size=os.fstat(f.fileno()).st_size
        if f.read(4)!=b'FORM': raise ValueError('Неизвестный формат игровых данных')
        f.seek(8)
        while f.tell()+8<=size:
            tag,length=struct.unpack('<4sI',f.read(8));start=f.tell()
            if start+length>size: raise ValueError('Повреждена таблица игровых данных')
            if tag==b'GEN8':
                if length<44: raise ValueError('Неполный GEN8')
                f.seek(start+40);pointer=struct.unpack('<I',f.read(4))[0]
                if not 4<=pointer<size: raise ValueError('Неверный указатель имени')
                f.seek(pointer-4);count=struct.unpack('<I',f.read(4))[0]
                if not 1<=count<=256 or pointer+count>size: raise ValueError('Неверная длина имени')
                name=f.read(count).rstrip(b'\0').decode('utf-8')
                if name in ('.','..') or not name or any(c in name for c in '/\\\0'):
                    raise ValueError('Небезопасное имя папки игры')
                return name
            f.seek(start+length)
    raise ValueError('В игровых данных нет GEN8')


def steam_installs(home):
    roots={p.resolve() for p in (home/'.local/share/Steam',home/'.steam/steam',home/'.steam/root') if p.exists()}
    for root in list(roots):
        try:
            raw=(root/'steamapps/libraryfolders.vdf').read_text()
            roots.update(Path(x.replace('\\\\','\\')).resolve() for x in re.findall(r'"path"\s+"([^"\n]+)"',raw))
        except OSError: pass
    result=[]
    for root in sorted(roots):
        try:
            text=(root/'steamapps/appmanifest_391540.acf').read_text()
            match=re.search(r'"installdir"\s+"([^"\n]+)"',text)
            if match and '/' not in match[1] and '\\' not in match[1] and match[1] not in ('.','..'):
                result.append((root/'steamapps/common'/match[1]).resolve())
        except OSError: pass
    return result


class Locator:
    def __init__(self,home=None,proc=Path('/proc')):
        self.home=Path(home or Path.home());self.proc=Path(proc);self.last=None;self.names={}

    def metadata(self,data):
        stat=data.stat();key=(str(data),stat.st_ino,stat.st_size,stat.st_mtime_ns)
        if key not in self.names:
            self.names={key:game_name(data)}
        name=self.names[key]
        if not (name.upper().startswith('UNDERTALE') or name.upper().startswith('NXTALE')):
            raise ValueError('Это не известная сборка Undertale')
        return name

    def running(self):
        found=[]
        for entry in self.proc.iterdir():
            if not entry.name.isdigit(): continue
            try:
                exe=Path(os.readlink(entry/'exe'))
                if exe.name.lower() not in ('runner','undertale'): continue
                cwd=Path(os.readlink(entry/'cwd'))
                argv=(entry/'cmdline').read_bytes().decode(errors='replace').split('\0')
                data=None
                if '-game' in argv:
                    candidate=Path(argv[argv.index('-game')+1])
                    data=candidate if candidate.is_absolute() else cwd/candidate
                else:
                    data=next((p for p in (exe.parent/'assets/game.unx',cwd/'game.unx',exe.parent/'data.win') if p.is_file()),None)
                if data is None: continue
                name=self.metadata(data)
                env={}
                for field in (entry/'environ').read_bytes().split(b'\0'):
                    key,sep,value=field.partition(b'=')
                    if key==b'HOME' and sep: env['HOME']=value.decode()
                home=Path(env.get('HOME',str(self.home)))
                if not home.is_absolute(): continue
                save=home/'.config'/name
                # Ignore our isolated bwrap QA runs: their paths spell the same
                # but refer to different mounted files, not the user's saves.
                root=entry/'root'
                isolated=False
                for target in (data,save):
                    visible=root/str(target).lstrip('/')
                    if visible.exists() and target.exists() and not os.path.samestat(visible.stat(),target.stat()): isolated=True
                if isolated: continue
                found.append(dict(pid=int(entry.name),game_dir=str(exe.parent),cwd=str(cwd),data=str(data),save_dir=str(save),name=name,source='Запущенный процесс + имя сборки GEN8',confidence='detected'))
            except (OSError,ValueError,IndexError,struct.error,UnicodeError): continue
        return found

    def detect(self):
        running=self.running()
        if len(running)==1:
            self.last=running[0];return dict(self.last)
        if len(running)>1:
            return dict(confidence='ambiguous',error='Запущено несколько Undertale. Автоматическая запись заблокирована.',candidates=running)
        installs=steam_installs(self.home)
        if self.last and Path(self.last['game_dir']) in installs:
            installs=[Path(self.last['game_dir'])]
        candidates=[]
        for folder in installs:
            try:
                data=folder/'assets/game.unx';name=self.metadata(data)
                candidates.append(dict(pid=None,game_dir=str(folder),cwd=None,data=str(data),save_dir=str(self.home/'.config'/name),name=name,source='Установленная Steam-сборка + имя GEN8; игра закрыта',confidence='detected'))
            except (OSError,ValueError,struct.error,UnicodeError): continue
        if len(candidates)==1:return candidates[0]
        return dict(confidence='ambiguous' if candidates else 'unknown',error='Не удалось однозначно определить рабочую папку. Автоматическая запись заблокирована.',candidates=candidates)
