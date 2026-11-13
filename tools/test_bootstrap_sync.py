"""Offline bootstrap/sync regression: no package install, GitHub call or real progress write."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import kur
from engine import senkron as S


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pafta_sync_review_')
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'PAFTA_DATA': self.temp.name})
        self.env.start(); self.addCleanup(self.env.stop)
        self.addCleanup(patch.stopall)
        patch.object(S, 'gist_id', return_value='offline-test-gist').start()
        self.stdout = contextlib.redirect_stdout(io.StringIO())
        self.stdout.__enter__(); self.addCleanup(self.stdout.__exit__, None, None, None)

    def progress(self, lesson):
        data = copy.deepcopy(S.BOS)
        data['tracks'] = {'python': {'steps': {lesson: {'done': True}}, 'drafts': {}, 'review': {}}}
        return data

    def test_push_preserves_both_machines_and_backups(self):
        local, remote = self.progress('p01:1'), self.progress('p02:1')
        S.save_atomik(S.local_path(), local)
        with patch.object(S, 'remote_get', return_value=remote), patch.object(S, 'remote_put') as put:
            S.yolla()
        sent = put.call_args.args[1]
        self.assertEqual(S.tamamlanan(sent), 2)
        self.assertEqual(S.load_json(S.local_path(), {}), sent)
        self.assertEqual(len(list((Path(self.temp.name)/'senkron-yedekleri').glob('*.json'))), 2)

    def test_failed_upload_does_not_overwrite_local(self):
        local = self.progress('p01:1'); S.save_atomik(S.local_path(), local)
        with patch.object(S, 'remote_get', return_value=self.progress('p02:1')), patch.object(S, 'remote_put', side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError): S.yolla()
        self.assertEqual(S.load_json(S.local_path(), {}), local)

    def test_corrupt_local_does_not_send_empty_progress(self):
        Path(S.local_path()).write_text('{broken', encoding='utf-8')
        with patch.object(S, 'remote_put') as put:
            with self.assertRaises(json.JSONDecodeError): S.yolla()
        put.assert_not_called()

    def test_exam_number_collision_and_repeat_merge(self):
        a, b = copy.deepcopy(S.BOS), copy.deepcopy(S.BOS)
        a['sinav'] = {'sayac': 1, 'aktif': None, 'gecmis': [{'no': 1, 'yol': 'python', 'tarih': '2026-10-27', 'dogru': 4}]}
        b['sinav'] = {'sayac': 1, 'aktif': None, 'gecmis': [{'no': 1, 'yol': 'bash', 'tarih': '2026-10-27', 'dogru': 5}]}
        merged = S.merge(a, b)
        self.assertEqual(len(merged['sinav']['gecmis']), 2)
        self.assertEqual(len({g['no'] for g in merged['sinav']['gecmis']}), 2)
        self.assertGreaterEqual(merged['sinav']['sayac'], 2)
        self.assertEqual(len(S.merge(merged, b)['sinav']['gecmis']), 2)
        reverse = S.merge(b, merged)
        self.assertEqual(len(S.merge(merged, reverse)['sinav']['gecmis']), 2)

    def test_union_preserves_custom_track_fields(self):
        a, b = self.progress('p01:1'), self.progress('p02:1')
        b['tracks']['python']['future_metadata'] = {'keep': True}
        a['days'], b['days'] = ['2026-10-26'], ['2026-10-27']
        merged = S.merge(a, b)
        self.assertEqual(merged['days'], ['2026-10-26', '2026-10-27'])
        self.assertEqual(merged['tracks']['python']['future_metadata'], {'keep': True})

    def test_live_app_blocks_disk_and_remote_writes(self):
        S.save_atomik(str(Path(self.temp.name)/'instance.json'), {'port': 18765, 'token': 'test'})
        with patch.object(S.urllib.request, 'build_opener') as opener, patch.object(S, 'remote_put') as put:
            opener.return_value.open.return_value.__enter__.return_value = object()
            for command in (S.cek, S.yolla):
                with self.assertRaisesRegex(RuntimeError, 'Pafta açık'): command()
        put.assert_not_called()
        self.assertFalse(Path(S.local_path()).exists())

    def test_public_and_truncated_gist_are_rejected(self):
        for response in ({'public': True}, {'public': False, 'files': {'progress.json': {'content': '{}', 'truncated': True}}}):
            with patch.object(S, '_gh', return_value=json.dumps(response)):
                with self.assertRaises(ValueError): S.remote_get('test')

    def test_empty_remote_first_push_is_valid(self):
        data = self.progress('p01:1'); S.save_atomik(S.local_path(), data)
        with patch.object(S, 'remote_get', return_value=None), patch.object(S, 'remote_put') as put:
            S.yolla()
        self.assertEqual(put.call_args.args[1], data)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(kur, 'pip_target', return_value=0).start()
        patch.object(kur, 'ps1', return_value=0).start()
        patch.object(kur, 'arac', return_value=None).start()
        self.stdout = contextlib.redirect_stdout(io.StringIO())
        self.stdout.__enter__(); self.addCleanup(self.stdout.__exit__, None, None, None)

    def test_sync_only_does_not_install_and_propagates_failure(self):
        with patch('sys.argv', ['kur.py', '--senkron']), patch.object(kur, 'kosu', return_value=7):
            self.assertEqual(kur.main(), 7)
        kur.pip_target.assert_not_called(); kur.ps1.assert_not_called()

    def test_requested_elastic_starts_real_services(self):
        with patch('sys.argv', ['kur.py', '--elastic']), patch.object(kur, 'pyscript', return_value=0) as script:
            self.assertEqual(kur.main(), 0)
        self.assertIn(unittest.mock.call('tools/elastic_lab_setup.py', '--pull', '--start'), script.call_args_list)

    def test_requested_lab_failure_is_nonzero(self):
        with patch('sys.argv', ['kur.py', '--elastic']), patch.object(kur, 'pyscript', return_value=1):
            with self.assertRaises(SystemExit) as result: kur.main()
        self.assertNotEqual(result.exception.code, 0)

    def test_ad_vm_is_started_and_provisioned(self):
        with patch('sys.argv', ['kur.py', '--advm']), patch.object(kur, 'pyscript', return_value=0) as script:
            kur.main()
        script.assert_called_once_with('tools/setup_ad_vm.py', '--start', '--provision')

    def test_unimplemented_ai_cannot_report_ready(self):
        with patch('sys.argv', ['kur.py', '--ai']):
            with self.assertRaises(SystemExit) as result: kur.main()
        self.assertNotEqual(result.exception.code, 0)

    def test_check_mode_has_no_install(self):
        with patch('sys.argv', ['kur.py', '--kontrol']): kur.main()
        kur.pip_target.assert_not_called(); kur.ps1.assert_not_called()

    def test_cim_server_path_is_sent_as_filename(self):
        from tools import splunk_cim_kur as C
        with patch('sys.argv', ['splunk_cim_kur.py', '--install']), \
             patch.object(C, 'verify_archive', return_value=Path('existing.tgz')), \
             patch.object(C, 'installed', side_effect=[False, True]), \
             patch.object(C.S, '_docker', return_value=(0, '', '')), \
             patch.object(C.S, 'istek') as request:
            C.main()
        create = next(c for c in request.call_args_list if c.args[0] == '/services/apps/local')
        self.assertEqual(create.args[1]['filename'], 'true')
        self.assertEqual(create.args[1]['name'], '/tmp/pafta-cim-850.tgz')


if __name__ == '__main__': unittest.main(verbosity=2)
