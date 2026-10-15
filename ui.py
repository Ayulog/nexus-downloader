import sys
import threading
import time
from collections import deque

from rich.console import Console, Group
from rich.markup import escape
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn
from rich.rule import Rule
from rich.text import Text

import config

sys.stdout.reconfigure(encoding="utf-8")
console = Console(force_terminal=True, color_system="truecolor", legacy_windows=False, no_color=False)

progress = Progress(
    TextColumn("[cyan]{task.description}"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>5.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
    TextColumn("{task.fields[status]}"),
    console=console,
)

stats = {
    "total": 0, "processed": 0, "downloaded": 0, "skipped": 0, "failed": 0,
    "bytes": 0, "todo_bytes": 0, "scanned": 0, "stopping": False,
}
stats_lock = threading.Lock()
started = time.time()
failures = []

log_lines = deque(maxlen=config.LOG_LINES)
log_lock = threading.Lock()
log_path = None
LOG_STYLES = {"OK": "green", "SKIP": "dim", "INFO": "cyan", "RETRY": "yellow", "FAIL": "red"}


def open_log():
    global log_path
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = config.LOG_DIR / f"{time.strftime('%Y-%m-%d_%H-%M-%S')}.log"
    return log_path


def write_log(text):
    if log_path is not None:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def log(level, msg):
    with log_lock:
        log_lines.append(f"[dim]{time.strftime('%H:%M:%S')}[/] [{LOG_STYLES[level]}]{level:<5}[/] {escape(msg)}")
        write_log(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {level:<5}  {msg}")


def record_failure(mod_label, item, reason):
    log("FAIL", f"{mod_label} | {reason}")
    with stats_lock:
        stats["failed"] += 1
        failures.append((mod_label, item, reason))


def size_str(num_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} B"
        num_bytes /= 1024


def hms(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def short(name):
    width = config.NAME_WIDTH
    name = name if len(name) <= width else name[:width - 1] + "…"
    return escape(name.ljust(width))


class Header:
    def __rich__(self):
        elapsed = time.time() - started
        done, total, scanned = stats["processed"], stats["total"], stats["scanned"]
        speed = stats["bytes"] / elapsed if elapsed > 0 else 0
        todo = stats["todo_bytes"] / scanned * total if 0 < scanned < total else stats["todo_bytes"]
        remaining = max(todo - stats["bytes"], 0)
        eta = hms(remaining / speed) if speed else "-:--:--"
        if scanned < total:
            eta = f"~{eta}"
        title = "[bold yellow]Stopping[/]" if stats["stopping"] else "[bold cyan]Downloading[/]"
        return Rule(
            f"{title} [bold]{done}/{total}[/] mods • {size_str(stats['bytes'])}"
            f" / {size_str(stats['bytes'] + remaining)} • {speed / 1024 ** 2:.1f} MB/s • elapsed {hms(elapsed)} • eta {eta}"
            + (f" • [dim]scanning {scanned}/{total}[/]" if scanned < total else "")
            + (f" • [red]{stats['failed']} failed[/]" if stats["failed"] else ""),
            style="cyan",
        )


class LogView:
    def __rich__(self):
        with log_lock:
            lines = []
            for line in log_lines:
                text = Text.from_markup(line, overflow="ellipsis")
                text.no_wrap = True
                lines.append(text)
            return Group(*lines)


def view():
    return Group("", Header(), "", progress, "", Rule("[dim]log[/]", style="dim"), LogView())


def finish():
    elapsed = hms(time.time() - started)
    summary = (
        f"{stats['downloaded']} downloaded ({size_str(stats['bytes'])}), "
        f"{stats['skipped']} skipped, {stats['failed']} failed, took {elapsed}"
    )
    with log_lock:
        write_log("")
        write_log("=" * 80)
        write_log(f"SUMMARY  {summary}")
        if failures:
            write_log("FAILED:")
            for mod_label, item, reason in failures:
                write_log(f"  - {mod_label}\n      {item}\n      {reason}")
        write_log("=" * 80)

    console.print(
        f"\n[bold green]Done[/] in {elapsed} • [green]{stats['downloaded']} downloaded[/] "
        f"({size_str(stats['bytes'])}) • {stats['skipped']} skipped • [red]{stats['failed']} failed[/]"
    )
    for mod_label, item, reason in failures:
        console.print(f"  [red]✗[/] {escape(mod_label)} [dim]— {escape(reason)}[/]")
    if log_path:
        console.print(f"[dim]Log: {log_path}[/]")
