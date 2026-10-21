"""Offline integration tests; never read the user's Nexus session."""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkerTests(unittest.TestCase):
    def run_isolated(self, script):
        with tempfile.TemporaryDirectory() as directory:
            for source in ROOT.glob('*.py'):
                shutil.copy(source, directory)
            shutil.copy(ROOT / 'config.example.toml', directory)
            result = subprocess.run([sys.executable, '-c', script], cwd=directory, capture_output=True, text=True, encoding='utf-8', timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout

    def test_original_archive_name_and_single_game_folder_are_preserved(self):
        self.run_isolated('\nimport downloader as d\nfilename = "Grandpa\'s Farm-3753-1-15-11-1751325509.zip"\nd.mod_info = lambda *args: {\'name\': "Grandpa\'s Farm"}\nd.mod_files = lambda *args: [{\'file_id\': 12345, \'file_name\': filename, \'name\': \'Main\', \'version\': \'1\'}]\nold = d.DOWNLOAD_DIR / \'stardewvalley\' / \'Old mod (3753)\'\nold.mkdir(parents=True)\n(old / \'test.zip\').write_bytes(b\'old\')\n_, folder, items = d.scan_mod(\'stardewvalley\', 3753)\nassert folder == d.DOWNLOAD_DIR / \'stardewvalley\'\nassert items[0][1].name == filename, items[0][1].name\nitems[0][1].write_bytes(b\'complete\')\nassert d.scan_mod(\'stardewvalley\', 3753)[2][0][3] is True\nassert (old / \'test.zip\').read_bytes() == b\'old\'\n')

    def test_conflicting_original_names_are_reported_without_renaming(self):
        self.run_isolated("\nimport downloader as d\nd.mod_info = lambda *args: {'name': 'Test mod'}\nd.mod_files = lambda *args: [{'file_id': 7, 'file_name': 'same.zip', 'name': 'Main', 'version': '1'}]\nd.scan_mod('stardewvalley', 42)\ntry:\n    d.scan_mod('stardewvalley', 43)\nexcept d.ModError as error:\n    assert 'same.zip' in str(error)\nelse:\n    raise AssertionError('different files claimed the same archive name')\n")

    def test_browser_login_can_be_cancelled_without_credentials(self):
        self.run_isolated('''
import threading
from unittest.mock import patch
import auth
assert hasattr(auth, 'stop_event'), 'shared cancellation is missing'
with patch.object(auth.webbrowser, 'open', return_value=True):
    timer = threading.Timer(0.05, auth.stop_event.set)
    timer.start()
    try:
        auth.browser_login()
    except InterruptedError:
        pass
    else:
        raise AssertionError('login ignored cancellation')
    finally:
        timer.join()
''')

    def test_worker_downloads_real_bytes_from_local_server(self):
        self.assertIsNotNone(importlib.util.find_spec('gui_worker'), 'GUI worker is not implemented')
        output = self.run_isolated('''
import http.server
import threading
from pathlib import Path
import downloader as d
import gui_worker
import sys
class OpenInput:
    def __iter__(self):
        threading.Event().wait()
        return iter(())
sys.stdin = OpenInput()
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', '12')
        self.end_headers()
        self.wfile.write(b'hello world!')
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
d.NEXUS_SESSION_COOKIE = 'offline-test'
d.get_token = lambda: 'offline-test'
d.REQUEST_DELAY_S = 0
d.MOD_LIST.write_text('https://www.nexusmods.com/stardewvalley/mods/42')
folder = Path('downloads/test')
f = {'file_id': 7, 'size_in_bytes': 12}
d.scan_mod = lambda domain, mod_id: ('Test mod', folder, [(f, folder / 'test.bin', folder / 'out', False)])
d.generate_download_url = lambda *args: f'http://127.0.0.1:{server.server_port}/file'
try:
    assert gui_worker.main('download') == 0
    assert (folder / 'test.bin').read_bytes() == b'hello world!'
    assert not list(folder.glob('*.part'))
finally:
    server.shutdown()
''')
        events = [json.loads(line) for line in output.splitlines()]
        self.assertTrue(any(e['type'] == 'snapshot' and e['stats']['downloaded'] == 1 for e in events))
        self.assertEqual(events[-1]['state'], 'done')

    def test_unexpected_run_error_stops_scanner_before_join(self):
        self.run_isolated('''
import downloader as d
d.NEXUS_SESSION_COOKIE = 'offline-test'
d.get_token = lambda: None
d.MOD_LIST.write_text('https://www.nexusmods.com/stardewvalley/mods/42')
class Scanner:
    def __init__(self, mods): pass
    def start(self): pass
    def join(self):
        assert d.stop_event.is_set(), 'exceptional exit must cancel the scanner before joining'
d.Scanner = Scanner
def fail(*args): raise ValueError('unexpected failure')
d.queue_mod = fail
try:
    d.run(headless=True)
except ValueError:
    pass
else:
    raise AssertionError('failure was swallowed')
''')

    def test_stop_before_queue_never_starts_download(self):
        self.run_isolated('''
import downloader as d
assert 'headless' in __import__('inspect').signature(d.run).parameters, 'headless entry point missing'
d.NEXUS_SESSION_COOKIE = 'offline-test'
d.get_token = lambda: d.stop_event.set()
d.MOD_LIST.write_text('https://www.nexusmods.com/stardewvalley/mods/42')
d.run(headless=True)
assert d.stats['downloaded'] == 0
assert not list(d.DOWNLOAD_DIR.rglob('*.part'))
''')


if __name__ == '__main__':
    unittest.main()
