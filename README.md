<h1 align="center">nexus-downloader</h1>

A command-line bulk downloader for [Nexus Mods](https://www.nexusmods.com). Drop
a list of mod links into `mods.txt` and it works through them one by one,
picking the right file, downloading it and optionally unpacking it. It logs in
the same way Vortex does (OAuth with PKCE) and talks to the Nexus API for
everything it can.

<p align="center">
  <a href="#highlights">Highlights</a> ·
  <a href="#setup">Setup</a> ·
  <a href="#run">Run</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#notes">Notes</a> ·
  <a href="#disclaimer">Disclaimer</a> ·
  <a href="#license">License</a>
</p>

## Highlights

- **Paste links, get mods**  
  One mod page link per line. The downloader resolves each to its main file,
  falls back to update/optional/misc files when a mod has no main file, and skips
  removed or hidden mods with a clear reason.

- **Clean live terminal view**  
  Progress, speed and time left for every download, a header with the overall
  size and ETA, the next three mods fading out below, and a running log.

- **Resumable and tidy**  
  Finished files are skipped on the next run, so you can stop with Ctrl+C at any
  time. Every mod lands in its own readable folder, e.g.
  `downloads/skyrimspecialedition/SkyUI (12604)/`, and archives (`.zip`, `.7z`,
  `.rar`) can be unpacked automatically.

## Setup

```bash
pip install -r requirements.txt
```

The first run creates `config.toml` and an empty `mods.txt`. Then:

1. Log in on nexusmods.com, open the browser dev tools (**Application >
   Cookies**) and copy the value of `nexusmods_session` into `session_cookie`
   in `config.toml`.
2. Put your mod links into `mods.txt`, one per line:

```
https://www.nexusmods.com/skyrimspecialedition/mods/12604
https://www.nexusmods.com/skyrimspecialedition/mods/266
```

## Run

```bash
python main.py
```

On the first start a browser window opens for the Nexus login. The session is
stored in `~/.nexus_session.json` and refreshed automatically after that.

## Configuration

Everything lives in `config.toml`:

| Setting | What it does |
|---|---|
| `file_categories` / `fallback_categories` | Which file categories to download, and what to try if a mod has none of them |
| `max_parallel` | Downloads at the same time (default 2) |
| `request_delay_s` | Pause between download link requests |
| `[extract] enabled` | Unpack archives after download, `delete_archive_after` removes them |
| `log_dir` | One log file per run with sizes, speeds and a failure summary |

## Notes

- Archives are unpacked with Python (`zipfile`, `py7zr`). `.rar` files and the
  few 7z variants py7zr can't read go through [7-Zip](https://www.7-zip.org)
  if it is installed.
- Download speed is whatever Nexus gives your account. Free accounts are
  throttled per account, so more parallel downloads won't make it faster.
- If every download suddenly fails with "session cookie probably expired",
  grab a fresh `nexusmods_session` cookie.

## Disclaimer

This is an independent, unofficial project and is not affiliated with, endorsed
by, or connected to Nexus Mods or Black Tree Gaming Ltd. It uses internal
endpoints that may change or break at any time.

You are responsible for how you use it: respect the Nexus Mods Terms of
Service, don't hammer their servers, and support the mod authors whose work you
download. No warranty of any kind; use at your own risk.

## License

[`MIT LICENSE`](LICENSE). Provided "as is", without warranty.
