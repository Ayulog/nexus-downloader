"""Package only explicit public artifacts; never copy local configuration."""
import hashlib
import importlib.metadata as metadata
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def main(version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Expected a semantic version such as 0.1.0')
    root = Path(__file__).resolve().parent
    release = root / 'release'
    release.mkdir(exist_ok=True)
    name = f'NexusDownloader-v{version}-windows-x64'
    archive = release / f'{name}.zip'
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary) / name
        folder.mkdir()
        for executable in ('NexusDownloader.exe', 'NexusDownloaderWorker.exe'):
            shutil.copy2(root / 'dist' / executable, folder / executable)
        for filename in ('LICENSE', 'README-GUI.zh-CN.md', 'config.example.toml'):
            shutil.copy2(root / filename, folder / filename)
        # Include distribution notices for bundled Python dependencies.
        for dist in metadata.distributions():
            package = dist.metadata['Name']
            for file in dist.files or ():
                if re.match(r'(?i)(license|copying|notice)', file.name):
                    source = Path(dist.locate_file(file))
                    if source.is_file():
                        target = folder / 'licenses' / package / file.name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
        runtime = Path(sys.base_prefix)
        runtime_licenses = list(runtime.glob('LICENSE*')) + list(runtime.rglob('license.terms'))
        for source in runtime_licenses:
            if source.is_file():
                target = folder / 'licenses' / 'Python-Tcl-Tk' / source.relative_to(runtime)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
            for source in sorted(folder.rglob('*')):
                if source.is_file():
                    output.write(source, source.relative_to(folder.parent))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix('.sha256')
    checksum.write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(f'Created release/{archive.name} ({archive.stat().st_size // 1024 // 1024} MB)')


if __name__ == '__main__':
    main(sys.argv[1])
