# nexus-downloader collaboration rules

- This is a standalone Python downloader, not a Stardew Valley MOD. Python 3.11+ is required (tomllib).
- Public authorship for new work: Ayulog. Git identity: Ayulog <65218314+Ayulog@users.noreply.github.com>.
- Preserve the original MIT copyright and third-party attribution. Never publish personal names, emails, account details, or machine-specific absolute paths.
- Keep cookies, sessions, mod lists, logs, downloads and local environments out of Git. Do not inspect or reuse personal credentials for automated tests.
- Preserve the CLI (`python main.py`), original Nexus authentication behavior and account limits when changing the GUI.
- Install dependencies with `python -m pip install -r requirements.txt`. Run offline tests with `python -m unittest discover -s tests -v`.
- Use relative paths in documentation. Keep task notes in ignored `.ai/tasks/<task-id>/handoff.md`.
- Inspect Git status before edits and preserve user changes. Do not modify sibling projects or treat the parent folder as a Git repository.
- A successful offline test does not establish real Nexus download compatibility. Clearly report when login and live downloads have not been tested.
