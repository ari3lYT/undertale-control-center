#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import copy
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import threading
import time
import webbrowser
from collections import deque
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from knowledge import enrich
from runtime import RuntimeLog
from bundles import GAME_FILES, FILE_HELP, Vault, read_bundle, write_bundle, coupled_bundle, digest, ini_bytes
from bonus import contextual_catalog, migration_plan, mode_from_config, NAMES as BONUS_NAMES, SANS_HOUSE, ROOM_MODES
import presets
import live_bundle
import timeline
from locations import Locator

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "dist"
CATALOG_PATH = APP_DIR / "data/catalog.json"
LOCATOR=Locator()
DETECTION=LOCATOR.detect()
AUTO_PROFILE=True
LAST_DISCOVERY=0.0
LIVE_DIR = Path(DETECTION.get('save_dir',str(Path.home()/'.config/UNDERTALE10th')))
SAVE_DIR = LIVE_DIR
GAME_DIR = Path(DETECTION.get('game_dir',str(Path.home()/'.local/share/Steam/steamapps/common/Undertale')))
GAME_DATA = Path(DETECTION.get('data',str(GAME_DIR/'assets/game.unx')))
STATE_DIR = Path.home() / ".local/share/undertale-control-center"
SNAPSHOT_DIR = STATE_DIR / "snapshots"
HISTORY_FILE = STATE_DIR / "history.jsonl"
MEMORY_FILE = STATE_DIR / "memory.jsonl"
WATCH_NAMES = GAME_FILES
WATCHED = {name: SAVE_DIR / name for name in WATCH_NAMES}
CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
enrich(CATALOG)
RUNTIME = RuntimeLog(LIVE_DIR / 'ucc-events.log')
ITEM_IDS = {x["id"] for x in CATALOG["items"]}
PHONE_IDS = {x["id"] for x in CATALOG["phones"]}
ROOM_IDS = {x["id"] for x in CATALOG["rooms"]}
SOUND_IDS = {x["id"] for x in CATALOG["sounds"]}
PLOT_VALUES = {float(x["value"]) for x in CATALOG["plots"]}
FLAG_META = {x["id"]: x for x in CATALOG["flags"]}
STATE_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
VAULT=Vault(STATE_DIR/'slots')
MANAGER_SETTINGS=STATE_DIR/'manager.json'
DEFAULT_SETTINGS={'write_mode':'coupled','wasd':True,'zxc':True,'debug':False,'input_log':True,'remember_view':True,'monitor_interval_ms':1000}

def discovery_state():
    profiles={str(p):p.name for p in (LIVE_DIR,Path.home()/'.config/UNDERTALE',Path.home()/'.config/UNDERTALE10th') if p.exists() or p==LIVE_DIR}
    return {**DETECTION,'automatic':AUTO_PROFILE,'selected':str(SAVE_DIR),'selection':'auto' if AUTO_PROFILE else str(SAVE_DIR),
            'profiles':[{'path':p,'name':n,'active':p==str(LIVE_DIR)} for p,n in profiles.items()]}

def refresh_location(force=False):
    global DETECTION,LIVE_DIR,SAVE_DIR,GAME_DIR,GAME_DATA,WATCHED,RUNTIME,LAST_DISCOVERY
    if not force and time.monotonic()-LAST_DISCOVERY<2: return
    LAST_DISCOVERY=time.monotonic()
    detected=LOCATOR.detect();DETECTION=detected
    if detected.get('confidence')!='detected': return
    live=Path(detected['save_dir'])
    GAME_DIR=Path(detected['game_dir']);GAME_DATA=Path(detected['data'])
    if live!=LIVE_DIR:
        LIVE_DIR=live;RUNTIME=RuntimeLog(live/'ucc-events.log')
    if AUTO_PROFILE and SAVE_DIR!=live:
        SAVE_DIR=live;WATCHED={n:live/n for n in WATCH_NAMES}
        MONITOR.last_bytes=MONITOR.read_set()
        MONITOR.snapshot('Автоматически выбрана рабочая папка: '+str(live),'control-center',[])

def manager_settings():
    try: return {**DEFAULT_SETTINGS,**json.loads(MANAGER_SETTINGS.read_text())}
    except (OSError,ValueError): return dict(DEFAULT_SETTINGS)

def require_stopped():
    if game_pid(): raise ValueError('Закрой Undertale перед изменением файлов. Для запущенной игры используй live-команду: иначе её память перезапишет файлы.')

def queue_live_bundle(after,title,expected,load_file=None):
    RUNTIME.poll();state=RUNTIME.state()
    if SAVE_DIR!=LIVE_DIR: raise ValueError('Live доступен только для рабочей папки запущенной игры.')
    if not game_pid() or not state['connected']: raise ValueError('Нет связи с игровым модулем.')
    if not state.get('live_bundle'): raise ValueError('В этой сессии модуль v5: live-загрузка всего сейва ещё не поддерживается. Новая сборка подготовлена отдельно; текущую игру мы не перезапускаем.')
    before=read_bundle(SAVE_DIR)
    if digest(before)!=expected: raise ValueError('Файлы изменились после проверки. Обнови план.')
    for name in ('file0','file9'):
        if after[name] is not None:
            errors=validate_model(parse_save_bytes(after[name]))['errors']
            if errors: raise ValueError(name+': '+errors[0]['message'])
    backup=VAULT.capture('Перед live: '+title,before,SAVE_DIR.name,'automatic-backup')
    result=live_bundle.prepare(SAVE_DIR,after,expected,state['monitor'].get('wall_ms',(state.get('current') or {}).get('wall_ms',0)),state['live_token'],load_file)
    result['backup']=backup['id']
    MONITOR._append_event({'id':str(result['seq']),'timestamp':now_iso(),'title':'Ожидает live: '+title,'cause':'control-center','changes':[]})
    return result

def commit_bundle(after,title,expected,live=False,load_file=None):
    if live: return queue_live_bundle(after,title,expected,load_file)
    require_stopped()
    before=read_bundle(SAVE_DIR)
    if digest(before)!=expected: raise ValueError('Файлы изменились после предпросмотра. Повтори проверку.')
    backup=VAULT.capture('Перед: '+title,before,SAVE_DIR.name,'automatic-backup')
    MONITOR.snapshot('Перед: '+title,'control-center',[])
    MONITOR.mark_self_write()
    write_bundle(SAVE_DIR,after,expected)
    MONITOR.last_bytes=MONITOR.read_set()
    changed=[n for n in after if after[n]!=before.get(n)]
    MONITOR.snapshot(title,'control-center',[{'label':n,'before':'отсутствует' if before[n] is None else len(before[n]),'after':'отсутствует' if after[n] is None else len(after[n]),'explanation':'Записан целый набор; прежний набор сохранён в слоте '+backup['id']} for n in changed])
    return {'ok':True,'files':changed,'backup':backup['id']}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def finite_number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def pretty_number(value):
    number = finite_number(value)
    if number is None:
        return str(value)
    return int(number) if number.is_integer() else number


def ticks_human(value) -> dict:
    ticks = int(finite_number(value) or 0)
    seconds = ticks / 30
    whole = int(seconds)
    days, rem = divmod(whole, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    label = (f"{days} д. " if days else "") + f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return {"ticks": ticks, "seconds": seconds, "days": days, "hours": hours, "minutes": minutes, "seconds_part": secs, "label": label}


def parse_save_bytes(raw: bytes) -> dict:
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    def get(index, default="0"):
        return lines[index].strip() if index < len(lines) else default
    invalid = []
    def num(index, default=0):
        value = finite_number(get(index, str(default)))
        if value is None: invalid.append(index + 1)
        return pretty_number(value if value is not None else default)
    inventory = [{"slot": i + 1, "item": num(12 + i * 2), "phone": num(13 + i * 2)} for i in range(8)]
    flags = [num(30 + i) for i in range(512)]
    model = {
        "line_count": len(lines), "name": get(0, "CHARA"), "lv": num(1, 1), "maxhp": num(2, 20),
        "maxen": num(3, 20), "at": num(4, 10), "weapon_strength": num(5), "df": num(6, 10),
        "armor_defense": num(7), "sp": num(8, 4), "xp": num(9), "gold": num(10), "kills": num(11),
        "inventory": inventory, "weapon": num(28, 3), "armor": num(29, 4), "flags": flags,
        "plot": num(542), "menu": [num(543 + i) for i in range(3)], "song": num(546, -1),
        "room": num(547), "time": num(548), "xbox_disconnect": num(549) if len(lines) > 549 else None,
        "xbox_coins": num(550) if len(lines) > 550 else None, "playtime": ticks_human(num(548)),
    }
    model['invalid_lines'] = sorted(set(invalid))
    return model


def read_save(name="file0") -> dict:
    path = WATCHED.get(name)
    if not path or not path.exists():
        raise FileNotFoundError(name)
    return parse_save_bytes(path.read_bytes())


def set_line(lines: list[str], index: int, value):
    while len(lines) <= index:
        lines.append("0")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    lines[index] = str(value) + (" " if index else "")


def path_to_line(path: str) -> int | None:
    simple = {"name": 0, "lv": 1, "maxhp": 2, "maxen": 3, "at": 4, "weapon_strength": 5,
              "df": 6, "armor_defense": 7, "sp": 8, "xp": 9, "gold": 10, "kills": 11,
              "weapon": 28, "armor": 29, "plot": 542, "song": 546, "room": 547, "time": 548,
              "xbox_disconnect": 549, "xbox_coins": 550}
    if path in simple:
        return simple[path]
    if path.startswith("flags."):
        idx = int(path.split(".")[1])
        if len(path.split('.')) != 2 or not 0 <= idx < 512: raise ValueError('Неверный индекс флага')
        return 30 + idx
    if path.startswith("inventory."):
        _, slot, kind = path.split(".")
        if not 0 <= int(slot) < 8 or kind not in ('phone','item'): raise ValueError('Неверный слот')
        return 12 + int(slot) * 2 + (1 if kind == "phone" else 0)
    if path.startswith("menu."):
        if len(path.split('.')) != 2 or not 0 <= int(path.split('.')[1]) < 3: raise ValueError('Неверное меню')
        return 543 + int(path.split(".")[1])
    return None


def value_at(model: dict, path: str):
    current = model
    for part in path.split("."):
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def set_model_value(model: dict, path: str, value):
    line = path_to_line(path)
    if line is None: raise ValueError('Неизвестное поле: '+path)
    if path != 'name' and finite_number(value) is None: raise ValueError('Нужно конечное число: '+path)
    if path == 'name' and (not isinstance(value,str) or '\n' in value or '\r' in value): raise ValueError('Имя должно быть одной строкой')
    model['invalid_lines'] = [n for n in model.get('invalid_lines',[]) if n != line+1]
    parts = path.split(".")
    current = model
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    last = parts[-1]
    if isinstance(current, list):
        current[int(last)] = value
    else:
        current[last] = value
    if path == "time":
        model["playtime"] = ticks_human(value)


def expected_lv(xp) -> int:
    thresholds = [0, 10, 30, 70, 120, 200, 300, 500, 800, 1200, 1700, 2500, 3500, 5000, 7000, 10000, 15000, 25000, 50000, 99999]
    x = finite_number(xp) or 0
    return max(i + 1 for i, threshold in enumerate(thresholds) if x >= threshold)


def validate_model(model: dict) -> dict:
    errors, warnings, suggestions = [], [], []
    def integer(value, fallback=-1):
        number = finite_number(value)
        return int(number) if number is not None and number.is_integer() else fallback
    def issue(level, path, message, suggestion=None, reason=None):
        target = errors if level == "error" else warnings
        target.append({"path": path, "message": message})
        if suggestion is not None:
            suggestions.append({"id": f"{path}:{suggestion}", "path": path, "value": suggestion, "reason": reason or message})
    if model.get("line_count", 549) < 549:
        errors.append({"path": "file", "message": "Файл короче 549 обязательных строк и не загрузится полностью."})
    for n in model.get('invalid_lines',[]):
        issue('error',f'строка {n}','В числовой строке не число. Подстановка нуля скрывала повреждение; запись заблокирована до исправления.')
    for i,v in enumerate(model['flags']):
        if finite_number(v) is None: issue('error',f'flags.{i}','Нужно конечное число.')
    for field in ('lv','maxhp','xp','gold','kills','time'):
        v = finite_number(model[field])
        if v is not None and (v < 0 or not v.is_integer()): issue('warning',field,'Для обычного прохождения требуется неотрицательное целое число.')
    for field in ("lv", "maxhp", "maxen", "at", "weapon_strength", "df", "armor_defense", "sp", "xp", "gold", "kills", "plot", "song", "room", "time"):
        if finite_number(model.get(field)) is None:
            issue("error", field, "Игра ожидает конечное число.")
    fun = finite_number(model["flags"][5])
    if fun is None or not 0 <= fun <= 100:
        issue("warning", "flags.5", "FUN вне используемого игрой диапазона 0–100.", max(0, min(100, int(fun or 0))), "Вернуть FUN в диапазон, который проверяет код игры.")
    for slot, entry in enumerate(model["inventory"]):
        if integer(entry["item"]) not in ITEM_IDS:
            issue("warning", f"inventory.{slot}.item", f"Неизвестный ID предмета {entry['item']}.", 0, "Пустой слот безопаснее неизвестного ID.")
        if integer(entry["phone"]) not in PHONE_IDS:
            issue("warning", f"inventory.{slot}.phone", f"Неизвестный ID телефона {entry['phone']}.", 0, "Игра знает только перечисленные контакты.")
    if integer(model["weapon"]) not in ITEM_IDS:
        issue("warning", "weapon", "Неизвестный ID экипированного оружия.", 3)
    if integer(model["armor"]) not in ITEM_IDS:
        issue("warning", "armor", "Неизвестный ID экипированной брони.", 4)
    room = integer(model["room"], -999)
    if room not in ROOM_IDS:
        issue("error", "room", f"Комнаты ID {room} нет в этой сборке.", 1, "Перейти в стартовую комнату.")
    song = integer(model["song"], -999)
    if song != -1 and song not in SOUND_IDS:
        issue("warning", "song", f"Звука ID {song} нет в этой сборке.", -1, "-1 разрешает комнате выбрать музыку самой.")
    plot = float(finite_number(model["plot"]) or 0)
    if plot not in PLOT_VALUES:
        nearest = min(PLOT_VALUES, key=lambda x: abs(x - plot))
        issue("warning", "plot", f"Значение plot={plot:g} не найдено среди этапов, которые код игры реально устанавливает.", pretty_number(nearest), "Ближайший реальный сюжетный этап.")
    real_lv = expected_lv(model["xp"])
    if int(finite_number(model["lv"]) or 0) != real_lv:
        issue("warning", "lv", f"EXP {model['xp']} соответствует LV {real_lv}, а записано LV {model['lv']}.", real_lv, "scr_levelup вычислит такой LV из текущего EXP.")
    expected_hp = 99 if real_lv == 20 else 16 + real_lv * 4
    expected_at = 8 + real_lv * 2
    expected_df = 9 + math.ceil(real_lv / 4)
    if int(finite_number(model["maxhp"]) or 0) != expected_hp:
        issue("warning", "maxhp", f"Для LV {real_lv} стандартный максимум HP — {expected_hp}.", expected_hp, "Формула scr_levelup: 16 + LV×4; на LV20 — 99.")
    if int(finite_number(model["at"]) or 0) != expected_at:
        issue("warning", "at", f"Для LV {real_lv} базовая AT — {expected_at}.", expected_at, "Формула scr_levelup: 8 + LV×2.")
    if int(finite_number(model["df"]) or 0) != expected_df:
        issue("warning", "df", f"Для LV {real_lv} базовая DF — {expected_df}.", expected_df, "Формула scr_levelup: 9 + ceil(LV/4).")
    for idx in (94, 360, 361, 362, 363, 364):
        if finite_number(model["flags"][idx]) != 0:
            issue("warning", f"flags.{idx}", f"flag[{idx}] всё равно сбрасывается загрузчиком.", 0, "Согласовать файл с поведением scr_load.")
    if model.get("xbox_coins") is not None and finite_number(model["xbox_coins"]) != finite_number(model["flags"][299]):
        issue("warning", "xbox_coins", "Отдельный счётчик Xbox не совпадает с flag[299].", model["flags"][299], "scr_saveprocess копирует flag[299] в xbox_coins_donated.")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "suggestions": suggestions, "summary": f"{len(errors)} ошибок · {len(warnings)} предупреждений · {len(suggestions)} предложений"}


def field_label(path: str) -> str:
    names = {"name": "Имя", "lv": "LV", "maxhp": "Максимум HP", "maxen": "Максимум EN", "at": "Базовая атака",
             "weapon_strength": "Сила оружия", "df": "Базовая защита", "armor_defense": "Защита брони", "sp": "Скорость",
             "xp": "EXP", "gold": "Золото", "kills": "Убийства", "weapon": "Оружие", "armor": "Броня",
             "plot": "Сюжетный этап", "song": "Музыка", "room": "Комната", "time": "Время", "xbox_coins": "Монеты святилища"}
    if path.startswith("flags."):
        idx = int(path.split(".")[1])
        meta = FLAG_META.get(idx, {})
        return f"flag[{idx}] — {meta.get('title', 'флаг')}"
    if path.startswith("inventory."):
        _, slot, kind = path.split(".")
        return f"Слот {int(slot)+1}: {'телефон' if kind == 'phone' else 'предмет'}"
    return names.get(path, path)


def semantic_diff(before: dict, after: dict) -> list[dict]:
    paths = ["name", "lv", "maxhp", "maxen", "at", "weapon_strength", "df", "armor_defense", "sp", "xp", "gold", "kills", "weapon", "armor", "plot", "song", "room", "time"]
    paths += [f"inventory.{i}.{kind}" for i in range(8) for kind in ("item", "phone")]
    paths += [f"flags.{i}" for i in range(512)]
    changes = []
    for path in paths:
        old, new = value_at(before, path), value_at(after, path)
        if old == new:
            continue
        explanation = "Значение изменилось."
        if path == "plot": explanation = "Игра перешла на другой сюжетный этап или редактор изменил позицию истории."
        elif path == "room": explanation = "Изменилась сохранённая комната — обычно это происходит при сохранении в новой точке."
        elif path == "time": explanation = f"Счётчик вырос на {pretty_number((finite_number(new) or 0) - (finite_number(old) or 0))} тиков."
        elif path.startswith("flags."):
            idx = int(path.split(".")[1]); meta = FLAG_META[idx]
            choices = {x['value']:x['label'] for x in meta.get('options',[])}
            explanation = f"{choices.get(old,old)} → {choices.get(new,new)}. {meta['purpose']}"
        elif ".item" in path: explanation = "Изменился предмет в инвентаре: его взяли, использовали, выбросили или заменили."
        elif ".phone" in path: explanation = "Изменился доступный пункт телефона."
        changes.append({"path": path, "label": field_label(path), "before": old, "after": new, "explanation": explanation})
    return changes


def read_ini(path: Path) -> dict:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    def unquote(value: str) -> str:
        value = value.strip()
        return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value
    return {section: {key: unquote(value) for key, value in parser.items(section)} for section in parser.sections()}


def update_ini(path: Path, section: str, key: str, value):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    output, in_section, written, section_found = [], False, False, False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_section and not written:
                output.append(f"{key}={value}"); written = True
            in_section = stripped[1:-1].casefold() == section.casefold()
            section_found = section_found or in_section
        if in_section and "=" in line and line.split("=", 1)[0].strip().casefold() == key.casefold():
            output.append(f"{key}={value}"); written = True
        else:
            output.append(line)
    if not section_found:
        if output and output[-1] != "": output.append("")
        output.extend([f"[{section}]", f"{key}={value}"])
    elif in_section and not written:
        output.append(f"{key}={value}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def game_pid() -> int | None:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit(): continue
        try:
            cmd = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
            exe = os.readlink(proc / 'exe')
            if exe == str(GAME_DIR / 'runner') or exe == str(GAME_DIR / 'UNDERTALE'):
                return int(proc.name)
        except (OSError, PermissionError):
            pass
    return None


def process_memory(pid: int | None) -> dict:
    if not pid:
        return {"running": False}
    result = {"running": True, "pid": pid, "timestamp": now_iso()}
    try:
        status = {}
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if ":" in line:
                key, value = line.split(":", 1); status[key] = value.strip()
        for src, dst in (("VmRSS", "rss_kb"), ("VmSize", "virtual_kb"), ("VmData", "data_kb"), ("VmSwap", "swap_kb"), ("RssAnon", "anon_kb"), ("RssFile", "file_kb"), ("Threads", "threads")):
            raw = status.get(src, "0").split()[0]
            result[dst] = int(raw)
        result["fds"] = len(list(Path(f"/proc/{pid}/fd").iterdir()))
        result["maps"] = sum(1 for _ in Path(f"/proc/{pid}/maps").open())
    except (OSError, ValueError):
        return {"running": False}
    return result


class Monitor:
    def __init__(self):
        self.lock = threading.RLock()
        self.last_bytes = self.read_set()
        self.timeline = deque(maxlen=1000)
        self.memory = deque(maxlen=1800)
        self.self_write_until = 0.0
        self.running = True
        self.last_pid = game_pid()
        self._load_history()
        if not self.timeline:
            self.snapshot("Мониторинг включён", "control-center", [])
        self.thread = threading.Thread(target=self._loop, name="undertale-monitor", daemon=True)
        self.thread.start()

    def _load_history(self):
        if not HISTORY_FILE.exists(): return
        try:
            for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines()[-1000:]:
                self.timeline.appendleft(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass

    def _append_event(self, event):
        self.timeline.appendleft(event)
        with HISTORY_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    @staticmethod
    def read_set():
        result = {}
        for name,path in WATCHED.items():
            try: result[name] = path.read_bytes()
            except FileNotFoundError: result[name] = None
        return result

    def snapshot(self, title: str, cause: str, changes: list[dict], changed_file: str | None = None, overrides: dict | None = None):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        folder = SNAPSHOT_DIR / stamp
        folder.mkdir(parents=True, exist_ok=True)
        observed = self.read_set() if overrides is None else overrides
        (folder/'profile.json').write_text(json.dumps({'save_dir':str(SAVE_DIR),'absent':[n for n,v in observed.items() if v is None]}))
        for name,raw in observed.items():
            if raw is not None: (folder/name).write_bytes(raw)
        event = {"id": stamp, "timestamp": now_iso(), "title": title, "cause": cause, "file": changed_file, "changes": changes, "snapshot": stamp}
        self._append_event(event)
        return event

    def mark_self_write(self):
        self.self_write_until = time.monotonic() + 3

    def _loop(self):
        memory_tick = 0
        while self.running:
            time.sleep(0.5)
            with self.lock:
                refresh_location()
                try: RUNTIME.poll()
                except OSError: pass  # The game can rotate/remove a file between stat and open.
                pid = game_pid()
                if pid != self.last_pid:
                    if pid:
                        self.snapshot("Undertale запущен", "game", [], None)
                    elif self.last_pid:
                        self.snapshot("Undertale завершён", "game", [], None)
                        # Our queued command must not unexpectedly affect a later game session.
                        (LIVE_DIR/'ucc-command.ini').unlink(missing_ok=True)
                    self.last_pid = pid
                try: observed = self.read_set()
                except OSError: continue
                differences = []
                cause = "control-center" if time.monotonic() < self.self_write_until else "game" if pid else "external"
                for name, raw in observed.items():
                    before_raw = self.last_bytes.get(name)
                    if raw == before_raw: continue
                    changes = []
                    if name.startswith("file") and before_raw and raw:
                        changes = semantic_diff(parse_save_bytes(before_raw), parse_save_bytes(raw))
                    else:
                        changes = [{"path": name, "label": name, "before": 'отсутствовал' if before_raw is None else hashlib.sha256(before_raw).hexdigest()[:8], "after": 'удалён' if raw is None else hashlib.sha256(raw).hexdigest()[:8], "explanation": 'Файл создан.' if before_raw is None else 'Файл удалён.' if raw is None else 'Изменилось содержимое; точная причина не установлена одним файловым diff.'}]
                    for change in changes: change['file'] = name
                    differences.extend(changes)
                if differences:
                    self.snapshot('До обнаруженного изменения файлов',cause,[],overrides=self.last_bytes)
                    self.snapshot(f'Обнаружено изменений: {len(differences)}',cause,differences,overrides=observed)
                    self.last_bytes = observed
                memory_tick += 1
                if memory_tick >= 4:
                    memory_tick = 0
                    sample = process_memory(pid)
                    if sample.get("running"):
                        previous = self.memory[-1] if self.memory else None
                        if previous and previous.get("pid") == sample.get("pid"):
                            sample["delta_rss_kb"] = sample.get("rss_kb", 0) - previous.get("rss_kb", 0)
                            sample["delta_virtual_kb"] = sample.get("virtual_kb", 0) - previous.get("virtual_kb", 0)
                        self.memory.append(sample)
                        with MEMORY_FILE.open("a", encoding="utf-8") as handle:
                            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")

    def state(self):
        pid = game_pid()
        saves = {}
        for name in ("file0", "file9"):
            try:
                model = read_save(name); saves[name] = {"model": model, "validation": validate_model(model)}
            except FileNotFoundError:
                saves[name] = None
        return {"game": process_memory(pid), "saves": saves, "ini": read_ini(WATCHED["undertale.ini"]) if WATCHED["undertale.ini"].exists() else {},
                "config": read_ini(WATCHED["config.ini"]) if WATCHED["config.ini"].exists() else {}, "paths": {"save": str(SAVE_DIR), "game": str(GAME_DIR)},
                "monitoring": True, "history_count": len(self.timeline), 'profile':SAVE_DIR.name,'live_profile':LIVE_DIR.name,'discovery':discovery_state()}

    def apply(self, save_name: str, changes: list[dict], accepted: list[str], expected_hash=None, mode='coupled', bundle_hash=None, live=False):
        if not live: require_stopped()
        all_before=read_bundle(SAVE_DIR)
        if bundle_hash and digest(all_before)!=bundle_hash: raise ValueError('Сопутствующие файлы изменились после проверки. Обнови план.')
        path = WATCHED.get(save_name)
        if save_name not in ("file0", "file9") or not path or not path.exists(): raise ValueError("Неизвестный файл сохранения")
        raw_before = path.read_bytes()
        if not expected_hash or hashlib.sha256(raw_before).hexdigest() != expected_hash:
            raise ValueError('Файл изменился после проверки. Открой новый план изменений: запись старого плана отменена.')
        before = read_save(save_name)
        after = copy.deepcopy(before)
        for change in changes:
            set_model_value(after, change["path"], change["value"])
        validation = validate_model(after)
        accepted_set = set(accepted)
        for suggestion in validation["suggestions"]:
            if suggestion["id"] in accepted_set:
                set_model_value(after, suggestion["path"], suggestion["value"])
        final_validation = validate_model(after)
        if final_validation["errors"]:
            raise ValueError("Изменение оставляет критические ошибки; сначала выбери исправления")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        all_paths = {c["path"] for c in changes} | {s["path"] for s in validation["suggestions"] if s["id"] in accepted_set}
        for field in all_paths:
            line = path_to_line(field)
            if line is None: continue
            set_line(lines, line, value_at(after, field))
        if live:
            raw='\n'.join(lines).encode('utf-8')
            target=coupled_bundle(all_before,save_name,raw,after,mode)
            result=queue_live_bundle(target,'Редактор '+save_name,digest(all_before),save_name)
            return {**result,'model':after,'validation':final_validation,'changes':semantic_diff(before,after)}
        self.snapshot(f"Перед изменением {save_name}", "control-center", semantic_diff(before, after), save_name)
        self.mark_self_write()
        if path.read_bytes() != raw_before: raise ValueError('Игра изменила файл во время проверки. Повтори проверку.')
        raw='\n'.join(lines).encode('utf-8')
        target=coupled_bundle(all_before,save_name,raw,after,mode)
        VAULT.capture('Перед правкой '+save_name,all_before,SAVE_DIR.name,'automatic-backup')
        write_bundle(SAVE_DIR,target,digest(all_before))
        self.last_bytes=self.read_set()
        self.snapshot(f"Применено к {save_name}", "control-center", semantic_diff(before, after), save_name)
        return {"model": after, "validation": final_validation, "changes": semantic_diff(before, after),'files':[n for n in target if target[n]!=all_before[n]]}

    def rollback(self, snapshot_id: str, live=False):
        folder = SNAPSHOT_DIR / snapshot_id
        if not folder.is_dir() or folder.resolve().parent != SNAPSHOT_DIR.resolve(): raise ValueError("Снимок не найден")
        if game_pid() and not live: raise ValueError('Для запущенной игры выбери live-откат с перезагрузкой игрового состояния.')
        meta = json.loads((folder/'profile.json').read_text()) if (folder/'profile.json').exists() else {'save_dir':str(Path.home()/'.config/UNDERTALE')}
        if meta['save_dir'] != str(SAVE_DIR): raise ValueError('Снимок относится к другой папке сохранений. Сначала выбери нужную папку.')
        if live:
            before=read_bundle(SAVE_DIR);after=dict(before)
            for name in GAME_FILES:
                if (folder/name).exists(): after[name]=(folder/name).read_bytes()
                elif name in meta.get('absent',[]): after[name]=None
            return queue_live_bundle(after,'Откат '+snapshot_id,digest(before))
        self.snapshot("Автоматический снимок перед откатом", "control-center", [])
        self.mark_self_write()
        restored = []
        for name, path in WATCHED.items():
            source = folder / name
            if source.exists(): atomic_write(path,source.read_bytes()); self.last_bytes[name] = path.read_bytes(); restored.append(name)
            elif name in meta.get('absent',[]):
                path.unlink(missing_ok=True)
                self.last_bytes[name] = None
                restored.append(name+' (отсутствовал — удалён; копия в защитном снимке)')
        self.snapshot(f"Откат к {snapshot_id}", "rollback", [{"label": name, "before": "текущее", "after": snapshot_id, "explanation": "Восстановлена версия файла из выбранного момента."} for name in restored])
        return restored


MONITOR = None


def atomic_write(path, raw):
    temporary = path.with_name(path.name+'.ucc-tmp')
    temporary.write_bytes(raw)
    os.replace(temporary,path)


def live_command(kind,index,value):
    RUNTIME.poll()
    if not game_pid() or not RUNTIME.state()['connected']:
        raise ValueError('Нет связи с игровым модулем. Запусти обновлённую игру; команда не поставлена в очередь.')
    if SAVE_DIR != LIVE_DIR:
        raise ValueError('Live относится к UNDERTALE10th. Сначала выбери эту папку, чтобы не смешать старый сейв с запущенной игрой.')
    command = LIVE_DIR / 'ucc-command.ini'
    if command.exists(): raise ValueError('Предыдущая команда ещё ждёт выхода из боя/диалога.')
    seq = int(time.time()*1000)
    MONITOR.snapshot('Перед live-командой','control-center',[])
    atomic_write(command,f'[command]\nseq={seq}\nkind={kind}\nindex={index}\nvalue={value}\n'.encode())
    return {'seq':seq,'message':'Команда отправлена. Игра подтвердит выполнение после выхода из боя/диалога. Сейв не записывается: для сохранения результата используй звезду.'}


class Handler(SimpleHTTPRequestHandler):
    server_version = "UndertaleControlCenter/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass

    def send_json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(raw)

    def read_json(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size > 2_000_000: raise ValueError("Слишком большой запрос")
        return json.loads(self.rfile.read(size) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path in ("/api/catalog", "/api/context"):
                live=RUNTIME.state()
                mode=mode_from_config(read_bundle(SAVE_DIR)['config.ini']);origin='config.ini выбранной папки'
                if SAVE_DIR==LIVE_DIR and live['connected'] and live.get('settings') and 'bonus' in live['settings']:
                    mode=live['settings']['bonus'];origin='память запущенной игры'
                if path == '/api/context':
                    return self.send_json({'mode':mode,'name':BONUS_NAMES[mode],'source':origin,'profile':SAVE_DIR.name})
                return self.send_json(contextual_catalog(CATALOG,mode,origin))
            if path == "/api/state": return self.send_json(MONITOR.state())
            if path == "/api/timeline":
                def memory_label(path):
                    if path.startswith('global.flag['):return field_label('flags.'+path[12:-1])
                    if path=='global.currentroom':return 'Комната продолжения (global.currentroom)'
                    return path
                def memory_explain(path):
                    if path.startswith('global.flag['):return FLAG_META.get(int(path[12:-1]),{}).get('purpose','')
                    if path=='global.currentroom':return 'scr_saveprocess записывает эту комнату в file0/file9. Во время боя видимая комната может отличаться от точки продолжения.'
                    return 'Наблюдаемое изменение в памяти игры; точное действие игрока одним diff не определяется.'
                technical=parse_qs(urlparse(self.path).query).get('technical',['0'])[0]=='1'
                return self.send_json({"events":timeline.project(list(MONITOR.timeline),RUNTIME.history(technical),memory_label,memory_explain)})
            if path == "/api/memory": return self.send_json({"current": process_memory(game_pid()), "samples": list(MONITOR.memory)[-300:]})
            if path == "/api/health": return self.send_json({"ok": True})
            if path == '/api/discovery': return self.send_json(discovery_state())
            if path == '/api/runtime': return self.send_json(RUNTIME.state())
            if path == '/api/variables':
                args = parse_qs(urlparse(self.path).query)
                return self.send_json(RUNTIME.variable_state(args.get('q',[''])[0][:200],
                    max(0,int(args.get('offset',['0'])[0])), max(1,min(500,int(args.get('limit',['200'])[0])))))
            if path == '/api/settings': return self.send_json(manager_settings())
            if path == '/api/live-status': return self.send_json(live_bundle.status(LIVE_DIR))
            if path == '/api/slots': return self.send_json({'slots':VAULT.list()})
            if path == '/api/presets': return self.send_json({'presets':presets.listing()})
            if path == '/api/files':
                bundle=read_bundle(SAVE_DIR)
                return self.send_json({'hash':digest(bundle),'files':[{'name':n,'exists':v is not None,'size':len(v) if v is not None else 0,'title':FILE_HELP[n][0],'description':FILE_HELP[n][1],'encoding':'hex' if n=='undertale.sav' else 'text','content':(v.hex() if n=='undertale.sav' else v.decode('utf-8',errors='replace')) if v is not None else ''} for n,v in bundle.items()]})
            return super().do_GET()
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self):
        with MONITOR.lock:
            refresh_location(force=True)
            return self.handle_post()

    def handle_post(self):
        global SAVE_DIR, WATCHED, AUTO_PROFILE
        path = urlparse(self.path).path
        try:
            origin = self.headers.get('Origin')
            if origin and urlparse(origin).hostname not in ('127.0.0.1','localhost'):
                return self.send_json({'error':'Запрос с постороннего сайта отклонён'},403)
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                return self.send_json({'error':'Требуется application/json'},415)
            body = self.read_json()
            guarded=('/api/apply','/api/apply-ini','/api/clean','/api/files/write','/api/slots/activate','/api/rollback','/api/bonus/apply','/api/bonus/live','/api/hot-flag','/api/force-fun')
            if path in guarded:
                if AUTO_PROFILE and DETECTION.get('confidence')!='detected': raise ValueError('Рабочая папка не подтверждена; запись заблокирована.')
                if self.headers.get('X-UCC-Save-Dir')!=str(SAVE_DIR): raise ValueError('Папка изменилась или страница устарела. Обнови страницу и проверь путь перед записью.')
            if path=='/api/presets/create':
                with MONITOR.lock:
                    preset,bundle,check=presets.build(body.get('id'),read_bundle(SAVE_DIR)['config.ini'],parse_save_bytes,validate_model)
                    record=VAULT.capture(preset['title'],bundle,SAVE_DIR.name,'external-preset:'+preset['id'])
                    return self.send_json({'slot':record,'validation':check})
            if path in ('/api/bonus/preview','/api/bonus/apply','/api/bonus/live'):
                with MONITOR.lock:
                    before=read_bundle(SAVE_DIR);target=body.get('target')
                    after,plan=migration_plan(before,target,parse_save_bytes,validate_model)
                    plan['hash']=digest(before)
                    if path=='/api/bonus/preview': return self.send_json(plan)
                    if plan['hash']!=body.get('hash'): raise ValueError('Состояние изменилось. Построй новый план смены бонуса.')
                    if path=='/api/bonus/live':
                        if (RUNTIME.state().get('current') or {}).get('room')!=SANS_HOUSE: raise ValueError('Для live-смены выйди в дом Санса, за пределы бонусной комнаты.')
                        if len(plan['changes'])>1: raise ValueError('Сейв находится в несовместимой комнате. Нужна файловая миграция при закрытой игре.')
                        VAULT.capture('Перед live-сменой бонуса',before,SAVE_DIR.name,'automatic-backup')
                        return self.send_json(live_command(3,0,target))
                    return self.send_json(commit_bundle(after,'Смена бонуса: '+BONUS_NAMES[target],plan['hash'],body.get('live') is True))
            if path == '/api/settings':
                settings=manager_settings()
                for key,value in body.items():
                    if key not in DEFAULT_SETTINGS: raise ValueError('Неизвестная настройка')
                    if key=='write_mode':
                        if value not in ('coupled','independent'): raise ValueError('Неизвестный режим')
                    elif key=='monitor_interval_ms':
                        if type(value)!=int or value not in (100,250,500,1000,2000): raise ValueError('Допустимые интервалы: 100, 250, 500, 1000 или 2000 мс')
                    elif not isinstance(value,bool): raise ValueError('Ожидается переключатель')
                    settings[key]=value
                atomic_write(MANAGER_SETTINGS,json.dumps(settings).encode())
                # Command bridge reads this separate, non-story INI; input is local to the game.
                atomic_write(LIVE_DIR/'ucc-settings.ini',ini_bytes(None,{'manager':{k:int(v) for k,v in settings.items() if isinstance(v,(bool,int))}}))
                return self.send_json(settings)
            if path == '/api/slots/create':
                with MONITOR.lock:
                    bundle={n:None for n in GAME_FILES} if body.get('clean') else read_bundle(SAVE_DIR)
                    return self.send_json(VAULT.capture(body.get('title') or 'Новый слот',bundle,SAVE_DIR.name))
            if path == '/api/slots/activate':
                with MONITOR.lock:
                    record,bundle=VAULT.get(str(body.get('id','')))
                    if record['profile']!=SAVE_DIR.name: raise ValueError('Слот из другой папки/сборки; автоматическая миграция запрещена.')
                    if record['source'].startswith('external-preset:') and body.get('accept_experimental') is not True: raise ValueError('Это сценарный внешний пресет, не подтверждённое целое прохождение. Нужен отдельный выбор принять риск.')
                    return self.send_json(commit_bundle(bundle,'Активация слота: '+record['title'],body.get('hash'),body.get('live') is True))
            if path == '/api/clean':
                if body.get('confirm')!='clean-all': raise ValueError('Нужно явное подтверждение чистого старта')
                with MONITOR.lock:
                    if SAVE_DIR!=LIVE_DIR and body.get('inactive_path')!=str(SAVE_DIR): raise ValueError('Выбрана не рабочая папка. Для очистки архива нужно отдельное подтверждение полного пути.')
                    return self.send_json(commit_bundle({n:None for n in GAME_FILES},'Чистый старт: локальные игровые файлы',body.get('hash'),body.get('live') is True))
            if path == '/api/files/write':
                with MONITOR.lock:
                    if not body.get('live'): require_stopped()
                    bundle=read_bundle(SAVE_DIR)
                    name=body.get('name')
                    if name not in GAME_FILES: raise ValueError('Неизвестный файл')
                    if digest(bundle)!=body.get('hash'): raise ValueError('Файлы изменились после открытия. Обнови редактор.')
                    content=body.get('content','')
                    if len(content)>1_000_000: raise ValueError('Файл слишком большой')
                    raw=None if body.get('remove') else bytes.fromhex(content) if name=='undertale.sav' else content.encode('utf-8')
                    if name=='config.ini' and mode_from_config(raw)!=mode_from_config(bundle[name]): raise ValueError('Для смены бонуса используй Настройки → план миграции.')
                    mode=body.get('mode','coupled')
                    if raw is not None and name.startswith('file'):
                        model=parse_save_bytes(raw);valid=validate_model(model)
                        if valid['errors']: raise ValueError('Неверный формат сейва: '+valid['errors'][0]['message'])
                        bundle=coupled_bundle(bundle,name,raw,model,mode)
                    else:
                        if name=='undertale.ini' and mode!='independent': raise ValueError('Сводку меняй в связанном редакторе сейва. Прямые сюжетные ключи INI доступны в независимом режиме.')
                        if raw and name.endswith('.ini'): ini_bytes(raw,{})
                        bundle[name]=raw
                    return self.send_json(commit_bundle(bundle,'Редактирование '+name,body['hash'],body.get('live') is True))
            if path == '/api/profile':
                name = body.get('profile')
                choices={p['path']:Path(p['path']) for p in discovery_state()['profiles']}
                if name in ('UNDERTALE','UNDERTALE10th'): name=str(Path.home()/'.config'/name)
                if name!='auto' and name not in choices: raise ValueError('Неизвестный профиль')
                with MONITOR.lock:
                    AUTO_PROFILE=name=='auto'
                    if AUTO_PROFILE and DETECTION.get('confidence')!='detected': raise ValueError('Автопоиск не нашёл однозначную рабочую папку')
                    SAVE_DIR = LIVE_DIR if AUTO_PROFILE else choices[name]
                    WATCHED = {n:SAVE_DIR/n for n in WATCHED}
                    MONITOR.last_bytes = MONITOR.read_set()
                return self.send_json({'ok':True,'profile':name})
            if path == "/api/preview":
                name = body.get('save','file0')
                if name not in ('file0','file9'): raise ValueError('Неизвестный сейв')
                raw = WATCHED[name].read_bytes()
                model = parse_save_bytes(raw); after = copy.deepcopy(model)
                for change in body.get("changes", []): set_model_value(after, change["path"], change["value"])
                mode=body.get('mode','coupled')
                return self.send_json({"changes": semantic_diff(model, after), "validation": validate_model(after), 'hash':hashlib.sha256(raw).hexdigest(),'bundle_hash':digest(read_bundle(SAVE_DIR)),'mode':mode,'files':['file0','file9','undertale.ini'] if mode=='coupled' else [name]})
            if path == "/api/apply":
                if not body.get('bundle_hash'): raise ValueError('Нужен новый предпросмотр всего набора файлов')
                with MONITOR.lock:
                    return self.send_json(MONITOR.apply(body.get("save", "file0"), body.get("changes", []), body.get("accepted", []),body.get('hash'),body.get('mode','coupled'),body.get('bundle_hash'),body.get('live') is True))
            if path == "/api/rollback":
                with MONITOR.lock:
                    result=MONITOR.rollback(str(body.get("snapshot", "")),body.get('live') is True)
                    return self.send_json(result if isinstance(result,dict) else {"restored":result})
            if path == "/api/backup":
                event = MONITOR.snapshot(body.get("title", "Ручной снимок"), "control-center", [])
                return self.send_json(event)
            if path == "/api/launch":
                if game_pid(): return self.send_json({"ok": True, "message": "Undertale уже запущен"})
                subprocess.Popen(["steam", "-applaunch", "391540"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return self.send_json({"ok": True, "message": "Команда запуска отправлена Steam"})
            if path == "/api/hot-flag":
                idx, value = finite_number(body["index"]), finite_number(body["value"])
                if idx is None or not idx.is_integer() or not 0 <= idx < 512 or value is None: raise ValueError("Неверный флаг или значение")
                with MONITOR.lock:
                    return self.send_json(live_command(1,int(idx),pretty_number(value)))
            if path == '/api/force-fun':
                value = finite_number(body['value'])
                if value not in (2,40,46,56,61,62,63,65,66,80,81,90): raise ValueError('Неизвестное FUN-событие')
                with MONITOR.lock:
                    return self.send_json(live_command(2,5,int(value)))
            if path == "/api/apply-ini":
                filename = body.get("file")
                allowed = {
                    "config.ini": {"General": {"lang", "sb", "ds"}, "joypad1": {"b0", "b1", "b2", "as", "jd"}},
                    "undertale.ini": {"General": {"Room", "Kills", "Time", "Love", "Name", "fun", "BC", "Gameover"}},
                }
                if filename not in allowed:
                    raise ValueError("Этот INI-файл не разрешён для записи")
                changes = body.get("changes", [])
                for change in changes:
                    section, key, value = change.get("section"), change.get("key"), change.get("value")
                    if section not in allowed[filename] or key not in allowed[filename][section]:
                        raise ValueError(f"Поле {section}/{key} не входит в известную схему игры")
                    if key == "lang" and value not in {"ru", "en", "ja"}:
                        raise ValueError("Допустимый язык: ru, en или ja")
                    if key == "ds" and (finite_number(value) is None or not 0 <= int(float(value)) <= 4):
                        raise ValueError("Бонусный набор должен быть от 0 до 4")
                    if key not in {"lang", "Name"} and finite_number(value) is None:
                        raise ValueError(f"{key}: игра ожидает конечное число")
                    if key=='ds' and finite_number(value)!=mode_from_config(read_bundle(SAVE_DIR)['config.ini']): raise ValueError('Смена бонуса доступна через план миграции в Настройках.')
                with MONITOR.lock:
                    if not body.get('live'): require_stopped()
                    if filename=='undertale.ini' and manager_settings()['write_mode']!='independent':
                        raise ValueError('Сводку INI меняй через связанный редактор сейва. Отдельная правка требует независимого режима.')
                    bundle=read_bundle(SAVE_DIR);updates={}
                    for c in changes: updates.setdefault(c['section'],{})[c['key']]=c['value']
                    bundle[filename]=ini_bytes(bundle[filename],updates)
                    return self.send_json(commit_bundle(bundle,'Настройки '+filename,body.get('bundle_hash'),body.get('live') is True))
            if path == "/api/open-folder":
                subprocess.Popen(["xdg-open", str(SAVE_DIR)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self.send_json({"ok": True})
            self.send_json({"error": "Неизвестный метод"}, 404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)


def main():
    global MONITOR
    MONITOR = Monitor()
    parser = argparse.ArgumentParser(description="Undertale Control Center")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"Undertale Control Center: {url}", flush=True)
    if not args.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        MONITOR.running = False; server.server_close()


if __name__ == "__main__":
    main()
