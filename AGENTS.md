# PrintQueueBridge

A macOS URL-scheme handler that opens 3MF files from Google Drive (Stream mode) directly in **PrusaSlicer or Bambu Studio**. Designed so a Trello card link opens the file with one click — no downloads, no copies. The slicer is chosen by which bridge URL the link points at.

## Architecture

Files in this repo split into two groups. The Mac side installs locally; the web side gets hosted as static HTTPS so Trello (which rejects custom URL schemes) can link into it.

| Repo file | Purpose | Deploys to |
|---|---|---|
| `handler.py` | Parses the URL, resolves the path under the Google Drive base, opens it in the chosen slicer, logs errors, shows Mac notifications on failure. | `~/Library/Application Support/PrintQueueBridge/handler.py` |
| `handler.applescript` | Tiny `on open location` shim that hands the URL to `handler.py`. Compiled to a `.app` bundle so LaunchServices can register it as the owner of the `printqueue://` scheme. | `/Applications/PrintQueueBridge.app` |
| `install.sh` | Copies the handler, compiles the AppleScript bundle, patches its `Info.plist` to declare the URL scheme, and re-registers it with LaunchServices. | (run in place) |
| `index.html` | Default bridge page (no `app` param → defaults to PrusaSlicer). Kept for backward compat. | static host root |
| `prusa/index.html` | Bridge that hardcodes `app=prusa`. Page title is "Open in PrusaSlicer" so Trello uses that as the attachment label. | `/prusa/` on the static host |
| `bambu/index.html` | Bridge that hardcodes `app=bambu`. Page title is "Open in Bambu Studio". | `/bambu/` on the static host |

Bundle ID: `com.blairjanis.printqueuebridge`. The bundle has `LSUIElement=true` so it never shows in the Dock.

End-to-end click path: Trello attachment (HTTPS) → browser loads the appropriate bridge page → JS redirects to `printqueue://open?file=X&app=Y` → LaunchServices hands off to `PrintQueueBridge.app` → AppleScript shells out to `handler.py` → `open -a <SlicerApp> <resolved path>`.

## Configuration (in `handler.py`)

- `BASE` — Google Drive root for printable files: `~/Library/CloudStorage/GoogleDrive-blairjanis@gmail.com/My Drive/Name Plates`
- `DEFAULT_FILENAME` — `name plate.3mf`. If the URL's `file=` value is a directory (or doesn't end in `.3mf`), this is appended. Lets Trello cards link to a folder name and "just work."
- `APPS` — short-key → macOS app name. Currently `{"prusa": "PrusaSlicer", "bambu": "BambuStudio"}`. Add a new slicer here (key + bundle name as it appears to `open -a`) to support it.
- `DEFAULT_APP` — used when the URL has no `app=` param. Currently `"prusa"`.
- `LOG_PATH` — `~/Library/Application Support/PrintQueueBridge/handler.log`

If you change any of the above, re-run `./install.sh` to push the new `handler.py` into the support dir.

## URL format

```
printqueue://open?file=<path-relative-to-BASE>[&app=<prusa|bambu>]
```

Examples:
- `printqueue://open?file=Acme%20Corp` → opens `…/Name Plates/Acme Corp/name plate.3mf` in PrusaSlicer (default)
- `printqueue://open?file=Acme%20Corp&app=bambu` → same file in Bambu Studio
- `printqueue://open?file=Acme%20Corp/lid.3mf` → opens that specific file

URL-encode spaces as `%20`. Don't put `printqueue://` URLs in Trello directly — Trello rejects custom schemes. Use the web bridge instead (next section).

## Web bridge

Trello rejects custom URL schemes — neither manual link attachments nor Butler will accept `printqueue://...`. The workaround is a tiny static HTML page hosted over HTTPS that reads `?file=X` from its query string and immediately redirects the browser to `printqueue://open?file=X&app=Y`. Trello sees a normal HTTPS URL and is happy; the browser handles the scheme jump.

There are three bridge pages, all near-identical:

- `index.html` (root) — defaults to PrusaSlicer. Kept for backward compat with any pre-existing links.
- `prusa/index.html` — title "Open in PrusaSlicer", redirects with `app=prusa`.
- `bambu/index.html` — title "Open in Bambu Studio", redirects with `app=bambu`.

Why three files instead of one with a `?app=` param? **Butler doesn't let you set the link attachment's display text** — it inherits the page `<title>` instead. Separate files mean each Trello attachment gets a self-explanatory label automatically.

**Hosting (GitHub Pages):** repo is at `https://github.com/blairjanis/openinslicer`, deploying from `main` branch root. Bridge URLs:

- `https://blairjanis.github.io/openinslicer/` — defaults to PrusaSlicer
- `https://blairjanis.github.io/openinslicer/prusa/` — explicit PrusaSlicer
- `https://blairjanis.github.io/openinslicer/bambu/` — Bambu Studio

**Updating the bridge:** edit the HTML file(s), commit and push, GitHub Pages redeploys in ~1 minute. No `install.sh` rerun needed since the bridge is web-hosted, not part of the local app.

## Trello setup (Butler "Create link" attachment)

With the bridges hosted, Butler's **Create link** action (under **Add/Remove**) can attach an HTTPS URL that points at the appropriate bridge with `{cardname}` substituted in. The user clicks the attachment → bridge loads → browser redirects to `printqueue://...` → handler opens the chosen slicer.

Two URLs to use:

| Slicer | URL pattern |
|---|---|
| PrusaSlicer | `https://blairjanis.github.io/openinslicer/prusa/?file={cardname}` |
| Bambu Studio | `https://blairjanis.github.io/openinslicer/bambu/?file={cardname}` |

`{cardname}` is a Butler variable — it substitutes the card title and URL-encodes spaces automatically. The `Name` field in the Create link action doesn't matter — Butler ignores it and uses the bridge page's `<title>` ("Open in PrusaSlicer" or "Open in Bambu Studio") as the attachment label.

### Option A — Rule on card creation (recommended)

Auto-attaches the link(s) to every new card. Zero per-card effort going forward. If most cards go to the same slicer, just make one rule with that bridge URL; if you want both buttons on every card, add two `Create link` actions.

1. Open the board's **Automation** menu → **Rules** → **Create Rule**.
2. **Trigger:** *when a card is added to* the relevant list (or just *when a card is created* if you use one board for prints).
3. **Add Action** → **Add/Remove** → **Create link**, URL set to one of the patterns above.
4. (Optional) Add a second **Create link** action for the other slicer.
5. Save the rule.

### Option B — Card button (for existing cards or one-offs)

The rule above only fires on *new* cards. For existing cards, define one card button per slicer, then click whichever you need.

1. Board Automation → **Card Buttons** → **Create Button**.
2. Title it (e.g. `Add PrusaSlicer link` / `Add Bambu link`), pick an icon.
3. **Add Action** → **Add/Remove** → **Create link**, with the matching bridge URL.
4. Save. Repeat for the other slicer.

### First-click flow

When you click the link attachment on a card, Trello opens the URL via your browser. The browser prompts something like *"Open PrintQueueBridge?"* — confirm, and (if offered) check **Always allow** so future clicks skip the prompt.

### Conventions and gotchas

- **Folder-name convention:** the card title must match a folder name under the Google Drive `BASE` path. The handler appends `DEFAULT_FILENAME` automatically, so `Acme Corp` resolves to `…/Name Plates/Acme Corp/name plate.3mf`.
- **Non-default file on a single card:** delete the auto-attached link and replace it with a hand-written one like `printqueue://open?file=Acme%20Corp/lid.3mf`.
- **Slashes in titles:** the handler treats `/` as a folder separator, so titles like `Acme/Lid` will look for a subfolder. Avoid slashes in card titles unless that's what you want.
- **Renaming a card:** the existing attachment keeps the *old* title in its URL. Either delete it and re-run the button, or update the URL by hand.

## Install / update / reset

**First install (or after editing any of the three files):**
```bash
cd ~/PrintQueueBridge
./install.sh
```
This is idempotent — it deletes and rebuilds `/Applications/PrintQueueBridge.app` every time, so it doubles as the update path.

**Verify the install:**
```bash
open 'printqueue://open?file=SOME_REAL_FOLDER_NAME'
tail -20 ~/Library/Application\ Support/PrintQueueBridge/handler.log
```

**Full reset (nuclear option):**
```bash
rm -rf /Applications/PrintQueueBridge.app
rm -rf ~/Library/Application\ Support/PrintQueueBridge
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user
./install.sh
```
Use this if LaunchServices gets confused about who owns the `printqueue://` scheme (e.g. after experimenting with multiple bundles).

## Troubleshooting

- **Nothing happens / "no application set to open the URL"** — LaunchServices didn't pick up the registration. Re-run `./install.sh`; if that fails, do the full reset above.
- **Notification says "Not found: …"** — the resolved path doesn't exist on disk. Check the log for the exact path the handler tried; usually a typo in the Trello link or a folder that hasn't synced yet in Google Drive Stream.
- **Notification says "Missing file= parameter"** — the URL is malformed. Must be `printqueue://open?file=…`.
- **Notification says "Unknown app: …"** — the `app=` value isn't in `APPS` in `handler.py`. Check spelling or add a new entry to `APPS` and re-run `./install.sh`.
- **Slicer doesn't launch** — confirm `open -a PrusaSlicer` (or `open -a BambuStudio`) works manually. The handler shells out to that. If `open -a` errors with "no application found," LaunchServices doesn't know about the app — open it once from Finder and try again.
- **No notifications appear at all** — check System Settings → Notifications and allow notifications for "PrintQueueBridge" (or for Script Editor, depending on macOS version).
- **Logs — first place to look when something doesn't work:**
  ```bash
  tail -20 ~/Library/Application\ Support/PrintQueueBridge/handler.log
  ```
  Every URL invocation is logged with timestamp. The 20-line tail is usually enough to see the last few attempts and the resolved path the handler tried to open.

## Notes for future changes

- The handler runs as a child of the AppleScript app bundle, which is launched by LaunchServices. There's no daemon, no launchd plist, nothing running in the background — the bundle is invoked on-demand per URL.
- If you rename the bundle ID, also update `BUNDLE_ID` in `install.sh` and run a full reset so LaunchServices forgets the old ID.
- `handler.py` uses `/usr/bin/python3` (system Python) via the AppleScript shim. Don't introduce dependencies that require a venv unless you also change the shim.
