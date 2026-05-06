#!/usr/bin/env python3
"""URL handler for printqueue:// — opens 3MF/SCAD files from Google Drive in the right app."""

import logging
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

BASE = Path.home() / "Library/CloudStorage/GoogleDrive-blairjanis@gmail.com/My Drive/Name Plates"
DEFAULT_FILENAME = "name plate.3mf"
SCAD_FILENAME = "name plate.scad"
SCAD_TEMPLATE = BASE / SCAD_FILENAME
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


def do_open(params: dict) -> None:
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


def do_prep(params: dict) -> None:
    file_param = params.get("file", [None])[0]
    if not file_param:
        raise ValueError("Missing file= parameter")

    folder = BASE / file_param
    target = folder / SCAD_FILENAME

    if not target.exists():
        if not SCAD_TEMPLATE.exists():
            raise FileNotFoundError(f"Template missing: {SCAD_TEMPLATE.relative_to(BASE.parent)}")
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCAD_TEMPLATE, target)
        logging.info("Created %s from template", target)

    logging.info("Opening %s with default app", target)
    subprocess.run(["open", str(target)], check=True)


ACTIONS = {"open": do_open, "prep": do_prep}


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

        action = parsed.netloc or "open"
        handler = ACTIONS.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action!r} (known: {', '.join(ACTIONS)})")

        params = urllib.parse.parse_qs(parsed.query)
        handler(params)
    except Exception as exc:
        logging.exception("Failed to handle URL")
        notify(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
