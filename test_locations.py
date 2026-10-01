import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from locations import Locator,game_name,steam_installs


def data_file(path,name='UNDERTALE10th'):
    text=name.encode()+b'\0';gen=bytearray(44);gen[1]=17
    struct.pack_into('<I',gen,40,72)
    payload=b'GEN8'+struct.pack('<I',44)+gen+b'STRG'+struct.pack('<I',4+len(text))+struct.pack('<I',len(text))+text
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'FORM'+struct.pack('<I',len(payload))+payload)
    return path


class LocationTests(unittest.TestCase):
    def test_header_uses_actual_build_name(self):
        with tempfile.TemporaryDirectory() as d:
            p=data_file(Path(d)/'game.unx');self.assertEqual(game_name(p),'UNDERTALE10th')
            data_file(p,'UNDERTALE');self.assertEqual(game_name(p),'UNDERTALE')

    def test_corrupt_and_unsafe_names(self):
        with tempfile.TemporaryDirectory() as d:
            p=data_file(Path(d)/'game.unx','../elsewhere')
            with self.assertRaises(ValueError):game_name(p)
            p.write_bytes(b'bad')
            with self.assertRaises(ValueError):game_name(p)

    def test_running_process_and_namespace(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);home=root/'home';game=root/'installation'
            data_file(game/'assets/game.unx');(game/'runner').touch()
            save=home/'.config/UNDERTALE10th';save.mkdir(parents=True)
            proc=root/'proc';entry=proc/'123';entry.mkdir(parents=True)
            (entry/'exe').symlink_to(game/'runner');(entry/'cwd').symlink_to(game)
            (entry/'root').symlink_to('/')
            (entry/'cmdline').write_bytes(str(game/'runner').encode()+b'\0')
            (entry/'environ').write_bytes(b'HOME='+str(home).encode()+b'\0SECRET=not-returned\0')
            result=Locator(home,proc).detect()
            self.assertEqual(result['save_dir'],str(save));self.assertEqual(result['pid'],123)
            self.assertNotIn('SECRET',str(result))
            (entry/'root').unlink();(entry/'root').mkdir()
            isolated=entry/'root'/str(save).lstrip('/');isolated.mkdir(parents=True)
            self.assertEqual(Locator(home,proc).running(),[])

    def test_steam_library_and_offline_selection(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);steam=home/'.local/share/Steam';library=home/'other-library'
            (steam/'steamapps').mkdir(parents=True);(library/'steamapps').mkdir(parents=True)
            (steam/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "1" { "path" "'+str(library)+'" } }')
            (library/'steamapps/appmanifest_391540.acf').write_text('"installdir" "MyUndertale"')
            folder=library/'steamapps/common/MyUndertale';data_file(folder/'assets/game.unx')
            proc=home/'proc';proc.mkdir()
            self.assertEqual(steam_installs(home),[folder])
            result=Locator(home,proc).detect()
            self.assertEqual(result['game_dir'],str(folder));self.assertIsNone(result['pid'])
            self.assertEqual(result['save_dir'],str(home/'.config/UNDERTALE10th'))

    def test_ambiguity_does_not_guess_by_mtime(self):
        locator=Locator()
        with patch.object(locator,'running',return_value=[{'pid':1},{'pid':2}]):
            result=locator.detect();self.assertEqual(result['confidence'],'ambiguous');self.assertNotIn('save_dir',result)

    def test_manual_selection_is_not_overwritten(self):
        import server as s
        result={'confidence':'detected','save_dir':str(s.LIVE_DIR),'game_dir':str(s.GAME_DIR),'data':str(s.GAME_DATA)}
        with patch.multiple(s,AUTO_PROFILE=False,SAVE_DIR=Path('/tmp/old-profile'),DETECTION={}),patch.object(s.LOCATOR,'detect',return_value=result):
            s.refresh_location(force=True)
            self.assertEqual(s.SAVE_DIR,Path('/tmp/old-profile'))

if __name__=='__main__':unittest.main()
