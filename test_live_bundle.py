import tempfile
import unittest
from pathlib import Path
from bundles import read_bundle,digest,GAME_FILES
from live_bundle import prepare,status
from runtime import RuntimeLog

class LiveBundleTests(unittest.TestCase):
    def test_staging_never_writes_active_files(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'file0').write_bytes(b'old')
            before=read_bundle(root);after=dict(before);after['file0']=b'new'
            r=prepare(root,after,digest(before),100,'123','file0')
            self.assertTrue(r['queued'])
            self.assertEqual(read_bundle(root),before)
            self.assertEqual((root/f"ucc-stage-{r['seq']}"/'after-file0').read_bytes(),b'new')
            with self.assertRaises(ValueError):prepare(root,after,digest(before),100,'123','file0')

    def test_stale_plan_and_unknown_file_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);before=read_bundle(root)
            with self.assertRaises(ValueError):prepare(root,before,'bad',1,'123')
            self.assertEqual(list(root.iterdir()),[])
            with self.assertRaises(ValueError):prepare(root,{**before,'../escape':b'x'},digest(before),1,'123')
            with self.assertRaises(ValueError):prepare(root,before,digest(before),1,'123','file0')
            self.assertEqual(list(root.iterdir()),[])

    def test_capability_token_survives_monitor_baseline(self):
        r=RuntimeLog(Path('/unused'));r.ingest('K|123');r.ingest('E|6')
        self.assertEqual(r.state()['live_token'],'123')
        self.assertTrue(r.state()['live_bundle'])

    def test_native_ini_quoted_result(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'ucc-live-result.ini').write_text('[result]\nseq="1789953064768.000000"\nstate="applied"\nreason=""\n')
            self.assertEqual(status(t),{'seq':'1789953064768','state':'applied','reason':''})

if __name__=='__main__':unittest.main()
