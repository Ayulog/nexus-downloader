"""GUI configuration helpers. Copyright (c) Ayulog; MIT licensed."""
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import tomlkit

from app_paths import BASE_DIR, TEMPLATE_DIR


def parse_links(text):
    links = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        url = urlsplit(line)
        match = re.fullmatch(r'/([A-Za-z0-9_]+)/mods/([1-9][0-9]*)/?', url.path)
        if url.scheme not in ('https', 'http') or url.netloc.lower() not in ('nexusmods.com', 'www.nexusmods.com') or not match:
            raise ValueError(f'第 {number} 行不是有效的 Nexus MOD 链接。')
        normalized = f'https://www.nexusmods.com/{match[1].lower()}/mods/{match[2]}'
        if normalized not in links:
            links.append(normalized)
    if not links:
        raise ValueError('请至少添加一个 Nexus MOD 链接。')
    return links


def read_document(path):
    source = path if path.exists() else TEMPLATE_DIR / 'config.example.toml'
    return tomlkit.parse(source.read_text(encoding='utf-8-sig'))


def load_settings(path):
    doc = read_document(path)
    return {
        'cookie': doc['nexus'].get('session_cookie', ''),
        'download_dir': doc['paths'].get('download_dir', 'downloads'),
        'parallel': doc['download'].get('max_parallel', 2),
        'extract': doc['extract'].get('enabled', False),
        'mod_list': doc['paths'].get('mod_list', 'mods.txt'),
    }


def atomic_write(path, text):
    temporary = path.with_name(path.name + '.tmp')
    try:
        temporary.write_text(text, encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def save_settings(path, *, cookie, download_dir, parallel, extract):
    if not isinstance(parallel, int) or not 1 <= parallel <= 32:
        raise ValueError('并行数量必须为 1–32 的整数。')
    if not download_dir.strip():
        raise ValueError('请选择下载目录。')
    doc = read_document(path)
    doc['nexus']['session_cookie'] = cookie.strip()
    doc['paths']['download_dir'] = download_dir.strip()
    doc['download']['max_parallel'] = parallel
    doc['download']['max_queued_links'] = max(parallel, doc['download'].get('max_queued_links', 3))
    doc['extract']['enabled'] = bool(extract)
    atomic_write(path, tomlkit.dumps(doc))


def worker_command(base_dir, mode):
    if getattr(sys, 'frozen', False):
        return [str(base_dir / 'NexusDownloaderWorker.exe'), mode]
    executable = Path(sys.executable)
    if executable.name.lower() == 'pythonw.exe':
        executable = executable.with_name('python.exe')
    return [str(executable), '-u', str(base_dir / 'gui_worker.py'), mode]
