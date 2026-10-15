import sys

try:
    from downloader import run
except ImportError as e:
    sys.exit(f"Missing dependency ({e.name}). Install with: pip install -r requirements.txt")

if __name__ == "__main__":
    run()
