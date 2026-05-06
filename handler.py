#!/usr/bin/env python3
"""URL handler for printqueue:// — opens 3MF files from Google Drive in PrusaSlicer."""

import logging
import subprocess
import sys
import urllib.parse
from pathlib import Path

BASE = Path.home() / "Library/CloudStorage/GoogleDrive-blairjanis@gmail.com/My Drive/Name Plates"
DEFAULT_FILENAME = "name plate.3mf"
APPS = {"prusa": "PrusaSlicer", "bambu": "BambuStudio"}
DEFAULT_APP = "prusa"
SUPPORT_DIR = Path.home() / "Library/Application Support/PrintQueueBridge"
LOG_PATH = SUPPORT_DIR / "handler.log"

SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def notify(message: str) -> None:
    safe = message.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e", f'display notification "{safe}" with title "Print Queue Bridge"'],
        check=False,
    )


def resolve(file_param: str) -> Path:
    target = BASE / file_param
    if target.is_dir() or not file_param.lower().endswith(".3mf"):
        target = target / DEFAULT_FILENAME
    if not target.exists():
        raise FileNotFoundError(f"Not found: {target.relative_to(BASE)}")
    return target


def main() -> None:
    if len(sys.argv) < 2:
        notify("No URL provided")
        sys.exit(1)

    url = sys.argv[1]
    logging.info("URL: %s", url)

    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "printqueue":
            raise ValueError(f"Unexpected scheme: {parsed.scheme!r}")

        params = urllib.parse.parse_qs(parsed.query)
        file_param = params.get("file", [None])[0]
        if not file_param:
            raise ValueError("Missing file= parameter")

        app_param = params.get("app", [DEFAULT_APP])[0]
        app_name = APPS.get(app_param)
        if not app_name:
            raise ValueError(f"Unknown app: {app_param!r} (known: {', '.join(APPS)})")

        target = resolve(file_param)
        logging.info("Opening %s with %s", target, app_name)
        subprocess.run(["open", "-a", app_name, str(target)], check=True)
    except Exception as exc:
        logging.exception("Failed to handle URL")
        notify(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
