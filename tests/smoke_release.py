"""Offline smoke check of a release ZIP on Windows; no Nexus credentials used."""
import json
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import psutil


def main(archive):
    with tempfile.TemporaryDirectory() as temporary:
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            assert not any(Path(name).name in {'config.toml', 'mods.txt', '.nexus_session.json'} for name in names)
            bundle.extractall(temporary)
        folder = next(Path(temporary).iterdir())
        result = subprocess.run([str(folder / 'NexusDownloaderWorker.exe'), 'download'],
                                cwd=folder, input='', capture_output=True, text=True, timeout=45)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        assert any(event.get('state') == 'authenticating' for event in events), result.stderr
        assert not any('ImportError' in event.get('message', '') or 'ModuleNotFoundError' in event.get('message', '') for event in events)
        assert events[-1]['type'] == 'result'
        assert (folder / 'config.toml').exists(), 'Configuration was not created beside the EXE'
        process = subprocess.Popen([str(folder / 'NexusDownloader.exe')], cwd=folder,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 40
            found = False
            while time.monotonic() < deadline and process.poll() is None:
                children = psutil.Process(process.pid).children(recursive=True)
                ids = ','.join(str(item.pid) for item in children + [psutil.Process(process.pid)])
                titles = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                                         f'Get-Process -Id {ids} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty MainWindowTitle'],
                                        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10).stdout
                if 'Nexus Downloader' in titles:
                    found = True
                    break
                time.sleep(0.2)
            assert found, 'Packaged GUI did not create its main window'
        finally:
            if process.poll() is None:
                children = psutil.Process(process.pid).children(recursive=True)
                for child in reversed(children):
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                if not children:
                    process.terminate()
                process.wait(timeout=15)
        print('Release smoke passed: worker JSON, local config, and actual GUI window; no Nexus request.')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
