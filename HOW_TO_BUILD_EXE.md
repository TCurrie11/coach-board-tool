# Building Coach Board Tool for Windows and Mac

This is for you, not for the coaches you're sending the tool to — they only
ever need the final app file (see "What to send coaches" under each OS
below).

Both platforms need to be built ON that platform — there's no way to
produce a Windows .exe or a Mac .app from Linux. You've got two GitHub
Actions workflows in this repo that do the building for you on GitHub's own
machines, so **you don't need a Windows PC or a Mac of your own** for either.

## One-time setup (covers both platforms)

1. Push this folder to a GitHub repo (private is fine).
2. Go to the repo's **Actions** tab. Two workflows should be there:
   **"Build Windows exe"** and **"Build macOS app"**. Both run automatically
   on every push, or you can click one and hit **Run workflow** manually.

## Getting the Windows exe

Wait for **"Build Windows exe"** to finish (green check, 2-4 minutes), open
that run, scroll to **Artifacts**, and download **CoachBoardTool-windows**.
Unzip it — `CoachBoardTool.exe` is the one file to send coaches.

**Windows SmartScreen:** since this isn't a code-signed app, Windows will
show a blue "Windows protected your PC" warning the first time each coach
runs it. They click **More info** → **Run anyway**. Worth a heads-up in
whatever message you send along with the file.

## Getting the Mac app

Wait for **"Build macOS app"** to finish, open that run, scroll to
**Artifacts**, and download **CoachBoardTool-macos-appleSilicon**. GitHub
wraps every download in its own zip, so unzip it once — inside is
**`CoachBoardTool-macos-appleSilicon.zip`**. *That* zip is what you send
coaches, as-is. Don't unzip it on Windows/Linux and re-zip it: that can
break the `.app` bundle inside.

When a coach unzips it on their Mac they get a **Coach Board Tool** folder
containing the app and a **READ ME FIRST.txt** that walks them through
installing it and the one-off security step below, so you don't have to
explain it yourself. (The guide's source is
[packaging/macos/READ ME FIRST.txt](packaging/macos/READ%20ME%20FIRST.txt).)

**Checked on a real Mac by CI:** before the zip is made, the workflow runs
the full test suite on macOS and then launches the finished app with
`--smoke-test`. That opens the real window, draws a play and exports an MP4
and a GIF; if any of it fails, the build goes red instead of producing a
broken download. The Windows workflow does the same for the `.exe`.

**This build only covers Apple Silicon Macs (M1 and newer)** — the ones
Apple has sold since late 2020. It will **not** run on an older Intel Mac.
If you know a coach is on one of those, see "Intel Macs" below.

**Gatekeeper (unsigned-app warning):** since this app isn't notarized by
Apple (that requires a paid $99/year Apple Developer account), the first
time a coach opens it they'll hit a security warning. The exact wording and
steps vary a bit by macOS version, so tell them this if it happens:

1. Double-click the app as normal. It'll say something like *"CoachBoardTool
   cannot be opened because it is from an unidentified developer"* — click
   **Done** (not Move to Trash).
2. Open the **Apple menu** → **System Settings** → **Privacy & Security**.
3. Scroll down to the **Security** section — there should be a line
   mentioning CoachBoardTool with an **Open Anyway** button next to it.
   Click it, and confirm with a password/Touch ID if asked.
4. Double-click the app again — it should now open (possibly with one more
   "Open" confirmation click).

This only has to happen once per Mac. On older macOS (Ventura and earlier),
right-clicking (or Control-clicking) the app and choosing **Open** is a
shortcut that skips straight to a confirmation dialog — worth trying first,
though newer macOS (Sequoia and later) has removed that shortcut, so
System Settings is the reliable path either way.

### Intel Macs

If a coach genuinely has an older Intel Mac, options are limited without a
paid Apple Developer setup for a universal build:
- Check **Apple menu → About This Mac** — if it says "Chip: Apple M1/M2/M3/M4..."
  they're on Apple Silicon and the normal build works fine.
- If it genuinely says an Intel processor, the practical fallback is
  running the app from source instead of a packaged app: they'd need
  Python 3.10+ installed (from python.org), then
  `pip install -r requirements.txt` and `python main.py` from this folder.
  That's real setup, not a double-click experience — worth checking whether
  this actually applies to anyone before worrying about it.

## Updating either app later

Whenever the app's source changes, just push again — both workflows rerun
automatically and you download the fresh artifacts the same way. There's no
separate "update" step.
