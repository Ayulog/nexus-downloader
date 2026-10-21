import importlib.util
import tempfile
import unittest
from pathlib import Path


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('gui_settings'), 'GUI settings are not implemented')
        import gui_settings
        self.settings = gui_settings

    def test_links_deduplicate_and_reject_lookalike_host(self):
        parse = self.settings.parse_links
        self.assertEqual(parse('https://www.nexusmods.com/stardewvalley/mods/42?tab=files\nhttps://nexusmods.com/stardewvalley/mods/42'), ['https://www.nexusmods.com/stardewvalley/mods/42'])
        for value in ['', 'https://evilnexusmods.com/game/mods/42', 'https://www.nexusmods.com/game/mods/0', 'not a link']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse(value)

    def test_settings_roundtrip_preserves_unexposed_values_and_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'config.toml'
            target.write_text(Path('config.example.toml').read_text() + '\n# keep me\n[custom]\nvalue = 42\n', encoding='utf-8')
            values = dict(cookie='a"b\\c', download_dir='中文目录', parallel=3, extract=True)
            self.settings.save_settings(target, **values)
            loaded = self.settings.load_settings(target)
            self.assertEqual({key: loaded[key] for key in values}, values)
            import tomllib
            data = tomllib.loads(target.read_text(encoding='utf-8'))
            self.assertEqual(data['custom']['value'], 42)
            self.assertEqual(data['download']['request_delay_s'], 4.0)
            self.assertIn('# keep me', target.read_text(encoding='utf-8'))

    def test_parallel_selection_is_not_limited_by_old_queue_size(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'config.toml'
            self.settings.save_settings(target, cookie='', download_dir='downloads', parallel=8, extract=False)
            import tomllib
            data = tomllib.loads(target.read_text(encoding='utf-8'))
            self.assertGreaterEqual(data['download']['max_queued_links'], 8)
            self.settings.save_settings(target, cookie='', download_dir='downloads', parallel=2, extract=False)
            data = tomllib.loads(target.read_text(encoding='utf-8'))
            self.assertGreaterEqual(data['download']['max_queued_links'], 8)

    def test_frozen_paths_and_worker_use_executable_directory(self):
        import runpy
        import sys
        from unittest.mock import patch
        self.assertIsNotNone(importlib.util.find_spec('app_paths'), 'packaged paths are not implemented')
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', str(Path('portable/NexusDownloader.exe').resolve())):
            paths = runpy.run_path('app_paths.py')
            self.assertEqual(paths['BASE_DIR'], Path('portable').resolve())
            self.assertEqual(self.settings.worker_command(Path('portable'), 'download'), [str(Path('portable/NexusDownloaderWorker.exe')), 'download'])

    def test_invalid_settings_do_not_overwrite_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'config.toml'
            target.write_text(Path('config.example.toml').read_text(), encoding='utf-8')
            before = target.read_bytes()
            for parallel, folder in [(0, 'downloads'), (33, 'downloads'), (2, '')]:
                with self.assertRaises(ValueError):
                    self.settings.save_settings(target, cookie='', download_dir=folder, parallel=parallel, extract=False)
                self.assertEqual(target.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
