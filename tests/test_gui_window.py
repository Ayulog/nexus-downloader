import importlib.util
import shutil
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('gui'), 'Desktop window is not implemented')
        from gui import App
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        shutil.copy('config.example.toml', self.base / 'config.toml')
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root, self.base)

    def tearDown(self):
        if hasattr(self, 'app'):
            if self.app.process:
                self.app.process.terminate()
                self.app.process.wait(timeout=5)
            self.root.after_cancel(self.app.after_id)
            self.root.update_idletasks()
            self.root.destroy()
            self.temp.cleanup()

    def pump_until(self, predicate):
        deadline = time.monotonic() + 8
        while not predicate() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.02)
        self.assertTrue(predicate(), 'GUI did not reach the expected state')

    def test_resize_keeps_actions_visible_and_narrow_content_scrollable(self):
        self.root.deiconify()
        for geometry in ('1100x800', '680x480', '1280x720'):
            with self.subTest(geometry=geometry):
                self.root.geometry(geometry)
                self.root.update()
                self.assertEqual(self.root.winfo_width(), int(geometry.split('x')[0]))
                for button in (self.app.start_button, self.app.stop_button):
                    self.assertTrue(button.winfo_ismapped())
                    bottom = button.winfo_rooty() - self.root.winfo_rooty() + button.winfo_height()
                    self.assertLessEqual(bottom, self.root.winfo_height())
                    self.assertGreaterEqual(button.winfo_height(), button.winfo_reqheight())
                if geometry == '680x480':
                    self.assertGreater(self.app.tasks.winfo_rooty(), self.app.login_button.winfo_rooty())
                    self.assertLess(self.app.canvas.yview()[1], 1.0)
                    self.app.canvas.yview_moveto(1.0)
                    self.root.update()
                    self.assertAlmostEqual(self.app.canvas.yview()[1], 1.0, places=2)

    def test_missing_cookie_rejected_before_start(self):
        self.app.links.insert('1.0', 'https://www.nexusmods.com/stardewvalley/mods/42')
        with patch('gui.messagebox.showerror'):
            self.app.start('download')
        self.assertIsNone(self.app.process)
        self.assertFalse((self.base / 'mods.txt').exists())

    def test_start_stop_and_second_run_reset_state(self):
        (self.base / 'gui_worker.py').write_text('''import json, sys
print(json.dumps({'type': 'state', 'state': 'running'}), flush=True)
print(json.dumps({'type': 'snapshot', 'stats': {'downloaded': 1, 'failed': 0, 'skipped': 0, 'scanned': 1, 'total': 1, 'bytes': 12, 'todo_bytes': 12}, 'tasks': [{'id': 0, 'name': 'test.zip', 'completed': 6, 'total': 12, 'speed': 3, 'status': ''}]}), flush=True)
for line in sys.stdin:
    if line.strip() == 'stop': break
print(json.dumps({'type': 'result', 'state': 'stopped'}), flush=True)
''', encoding='utf-8')
        self.app.cookie.set('offline-test')
        self.app.links.insert('1.0', 'https://www.nexusmods.com/stardewvalley/mods/42')
        for _ in range(2):
            self.app.start('download')
            self.assertIsNotNone(self.app.process)
            self.pump_until(lambda: len(self.app.tasks.get_children()) == 1)
            self.assertEqual(str(self.app.start_button['state']), 'disabled')
            self.app.stop()
            self.pump_until(lambda: self.app.process is None)
            self.assertIn('停止', self.app.status.get())
            self.assertEqual(str(self.app.start_button['state']), 'normal')
        self.assertIn('stardewvalley/mods/42', (self.base / 'mods.txt').read_text())


if __name__ == '__main__':
    unittest.main()
