"""Versioned local save bundles. Never silently equate checkpoint and star saves."""
import base64
import configparser
import hashlib
import io
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

GAME_FILES = tuple(f'file{i}' for i in range(10)) + ('undertale.ini','config.ini','system_information_962','system_information_963','undertale.sav')
FILE_HELP = {
 'file0':('Сохранение у звезды','Обычное продолжение читает file0. scr_save пишет выбранный сейв, затем file9, затем General/Name, Love, Time, Kills, Room в undertale.ini. В связанном режиме редактор повторяет эту группу записей.'),
 'file9':('Временная контрольная точка','scr_tempsave пишет только file9. После смерти scr_tempload может вернуть сюда, а не к звезде. Более новый file9 при старом file0 — допустимое состояние игры. Связанное редактирование file9 в менеджере намеренно становится новым общим checkpoint; для отдельной правки выбери независимый режим.'),
 'file8':('Контрольная точка перед финалом Флауи','Сценарий Азгора переключает global.filechoice на 8. Это служебная копия состояния для финальной последовательности, не второй пользовательский слот. Не заменяй ей file0 без проверки ветки и INI.'),
 'undertale.ini':('Сводка и память между прохождениями','General хранит сводку звезды и FUN. Отдельные секции хранят встречи, смерти, сбросы, Флауи, финалы и пароли Санса. Равенство всех ключей флагам НЕ требуется: часть памяти намеренно переживает загрузку и обычный Reset.'),
 'config.ini':('Язык, бонусы, рамка и геймпад','General/lang — язык; ds — вариант бонуса; sb — рамка. joypad1 содержит назначения b0/b1/b2 и параметры стика. Не является сюжетным сейвом. Чистый старт удаляет и эти настройки, обычная смена сюжетного пресета сохраняет их.'),
 'system_information_962':('Мир уничтожен','Наличие этого файла при отсутствии 963 направляет старт в пустоту после геноцида. Содержимое не является обычным сейвом. Удаление меняет память о концовке и должно быть отдельным осознанным действием.'),
 'system_information_963':('Соглашение после уничтожения мира','Игра создаёт файл после принятия соглашения в пустоте; он сохраняет след проданной души и влияет на последующие финалы. Обычный Reset не равен его удалению. Steam Cloud может вернуть облачную копию.'),
 'undertale.sav':('Контейнер платформенной версии','ossafe_savedata_save собирает файловое хранилище в бинарный буфер на консолях. Linux обычно использует отдельные файлы. Не разбирается как file0; редактор показывает байты и допускает явную замену HEX в независимом режиме.'),
}
for i in range(1,8):
    FILE_HELP[f'file{i}']=(f'Служебный номер {i}', 'scr_saveprocess формирует имя из global.filechoice. В штатных просмотренных ветках текущей сборки отдельного сценария записи этого номера не найдено; код уничтожения мира удаляет file0–file9. Это не готовый пользовательский слот. Если файл существует, доступен редактор содержимого, но связывать его с file0 автоматически нельзя.')

def digest(bundle):
    return hashlib.sha256(json.dumps({n:None if b is None else base64.b64encode(b).decode() for n,b in sorted(bundle.items())},sort_keys=True).encode()).hexdigest()

def read_bundle(root):
    result={}
    for name in GAME_FILES:
        path=root/name
        if path.is_symlink(): raise ValueError('Символическая ссылка вместо файла игры: '+name)
        try: result[name]=path.read_bytes()
        except FileNotFoundError: result[name]=None
    return result

def ini_bytes(raw, updates):
    cp=configparser.ConfigParser(interpolation=None,strict=False);cp.optionxform=str
    if raw: cp.read_string(raw.decode('utf-8-sig'))
    for section,values in updates.items():
        if not cp.has_section(section): cp.add_section(section)
        for key,value in values.items(): cp.set(section,key,str(value))
    out=io.StringIO();cp.write(out,space_around_delimiters=False)
    return out.getvalue().encode()

def coupled_bundle(before, selected, raw, model, mode='coupled'):
    if mode not in ('coupled','independent'): raise ValueError('Неизвестный режим записи')
    after=dict(before);after[selected]=raw
    if mode=='coupled' and selected in ('file0','file9'):
        after['file0']=after['file9']=raw
        after['undertale.ini']=ini_bytes(before.get('undertale.ini'),{'General':{
            'Name':model['name'],'Love':model['lv'],'Time':model['time'],'Kills':model['kills'],
            'Room':model['room'],'fun':model['flags'][5]}})
    return after

def write_bundle(root, bundle, expected=None):
    """Recover on failure. The caller must exclude a running game and hold its lock.
    Multiple file renames are not one OS-atomic operation; backup is retained externally.
    """
    before=read_bundle(root)
    if expected and digest(before)!=expected: raise ValueError('Набор файлов изменился после проверки. Обнови план.')
    if set(bundle)!=set(GAME_FILES): raise ValueError('Неполный набор файлов')
    root.mkdir(parents=True,exist_ok=True)
    def put(name,raw):
        target=root/name
        if target.is_symlink(): raise ValueError('Ссылка вместо файла: '+name)
        if raw is None: target.unlink(missing_ok=True)
        else:
            tmp=root/(name+'.ucc-tmp');tmp.write_bytes(raw);os.replace(tmp,target)
    try:
        for name,raw in bundle.items():
            if raw!=before.get(name): put(name,raw)
    except Exception:
        for name,raw in before.items(): put(name,raw)
        raise

class Vault:
    def __init__(self,root): self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def capture(self,title,bundle,profile,source='local'):
        ident=uuid.uuid4().hex
        record={'id':ident,'title':str(title)[:120],'created':datetime.now().astimezone().isoformat(),'profile':profile,'source':source,
            'files':{n:None if v is None else base64.b64encode(v).decode() for n,v in bundle.items()},'hash':digest(bundle)}
        (self.root/(ident+'.json')).write_text(json.dumps(record,ensure_ascii=False))
        return {k:v for k,v in record.items() if k!='files'}
    def get(self,ident):
        if not re.fullmatch('[0-9a-f]{32}',ident): raise ValueError('Неверный слот')
        r=json.loads((self.root/(ident+'.json')).read_text());b={n:None if v is None else base64.b64decode(v,validate=True) for n,v in r['files'].items()}
        if set(b)!=set(GAME_FILES) or digest(b)!=r['hash']: raise ValueError('Слот повреждён')
        return r,b
    def list(self):
        records=[]
        for p in sorted(self.root.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True):
            try:
                r,_=self.get(p.stem);records.append({k:v for k,v in r.items() if k!='files'})
            except (ValueError,OSError): continue
        return records
