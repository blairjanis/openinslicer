# PrintQueueBridge

A macOS URL-scheme handler that opens 3MF files from Google Drive (Stream mode) directly in PrusaSlicer. Designed so a Trello card link like `printqueue://open?file=MyPart` opens the file with one click — no downloads, no copies.

## Architecture

Four files in this repo. Three install onto the Mac; one (`index.html`) gets hosted on the web because Trello won't accept `printqueue://` URLs directly.

| Repo file | Purpose | Deploys to |
|---|---|---|
| `handler.py` | Parses the URL, resolves the path under the Google Drive base, opens it in PrusaSlicer, logs errors, shows Mac notifications on failure. | `~/Library/Application Support/PrintQueueBridge/handler.py` |
| `handler.applescript` | Tiny `on open location` shim that hands the URL to `handler.py`. Compiled to a `.app` bundle so LaunchServices can register it as the owner of the `printqueue://` scheme. | `/Applications/PrintQueueBridge.app` |
| `install.sh` | Copies the handler, compiles the AppleScript bundle, patches its `Info.plist` to declare the URL scheme, and re-registers it with LaunchServices. | (run in place) |
| `index.html` | Static HTTPS bridge page. Reads `?file=X` from the URL and redirects the browser to `printqueue://open?file=X`. Needed because Trello rejects custom URL schemes. | A static host (GitHub Pages, Netlify, etc.) |

Bundle ID: `com.blairjanis.printqueuebridge`. The bundle has `LSUIElement=true` so it never shows in the Dock.

End-to-end click path: Trello attachment (HTTPS) → browser loads `index.html` → JS redirects to `printqueue://...` → LaunchServices hands off to `PrintQueueBridge.app` → AppleScript shells out to `handler.py` → `open -a PrusaSlicer <resolved path>`.

## Configuration (in `handler.py`)

- `BASE` — Google Drive root for printable files: `~/Library/CloudStorage/GoogleDrive-blairjanis@gmail.com/My Drive/Name Plates`
- `DEFAULT_FILENAME` — `name plate.3mf`. If the URL's `file=` value is a directory (or doesn't end in `.3mf`), this is appended. Lets Trello cards link to a folder name and "just work."
- `LOG_PATH` — `~/Library/Application Support/PrintQueueBridge/handler.log`

If you change `BASE` or `DEFAULT_FILENAME`, re-run `./install.sh` to push the new `handler.py` into the support dir.

## URL format (for Trello attachments)

```
printqueue://open?file=<path-relative-to-BASE>
```

Examples:
- `printqueue://open?file=Acme%20Corp` → opens `…/Name Plates/Acme Corp/name plate.3mf`
- `printqueue://open?file=Acme%20Corp/lid.3mf` → opens that specific file

URL-encode spaces as `%20`. Add the link as a Trello card attachment; clicking it triggers the handler.

## Web bridge (`index.html`)

Trello rejects custom URL schemes — neither manual link attachments nor Butler will accept `printqueue://...`. The workaround is `index.html` in this repo: a 20-line static page hosted over HTTPS that reads `?file=X` from its query string and immediately redirects the browser to `printqueue://open?file=X`. Trello sees a normal HTTPS URL and is happy; the browser handles the scheme jump.

**Hosting (GitHub Pages, simplest free path):**

1. Create a public GitHub repo (e.g. `printqueue-bridge`) and push `index.html` to its `main` branch.
2. In the repo's **Settings → Pages**, set Source to **Deploy from a branch**, branch `main`, folder `/ (root)`. Save.
3. Wait ~1 minute, then your bridge URL is `https://<username>.github.io/<reponame>/`. Test it: `https://<username>.github.io/<reponame>/?file=test` should attempt to open PrusaSlicer.

Any HTTPS host will do (Netlify, Cloudflare Pages, your own server). The page is self-contained and has no dependencies.

**Updating the bridge:** edit `index.html`, push the change, GitHub Pages redeploys in ~1 minute. No app reinstall needed.

## Trello setup (Butler "Create link" attachment)

With the bridge hosted, Butler's **Create link** action (under **Add/Remove**) can attach an HTTPS URL that points at the bridge with `{cardname}` substituted in. The user clicks the attachment → bridge loads → browser redirects to `printqueue://` → handler opens PrusaSlicer.

Replace `<bridge-url>` below with your actual hosted URL (e.g. `https://blairjanis.github.io/printqueue-bridge/`).

### Option A — Rule on card creation (recommended)

Auto-attaches the link to every new card. Zero per-card effort going forward.

1. Open the board's **Automation** menu → **Rules** → **Create Rule**.
2. **Trigger:** *when a card is added to* the relevant list (or just *when a card is created* if you use one board for prints).
3. **Add Action** → **Add/Remove** → **Create link**.
4. Fill in:
   - **URL:** `<bridge-url>?file={cardname}`
   - **Name** (link title shown on the card): `Open in PrusaSlicer`
5. Save the action and save the rule.

`{cardname}` is a Butler variable — it substitutes the card title and URL-encodes spaces automatically.

### Option B — Card button (for existing cards or one-offs)

The rule above only fires on *new* cards. For existing cards, define a card button that does the same thing, then click it once per card.

1. Board Automation → **Card Buttons** → **Create Button**.
2. Title it (e.g. `Add PrusaSlicer link`), pick an icon.
3. **Add Action** → **Add/Remove** → **Create link**, with the same URL and Name as above.
4. Save.

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
- **PrusaSlicer doesn't launch** — confirm `open -a PrusaSlicer` works manually. The handler shells out to that.
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
