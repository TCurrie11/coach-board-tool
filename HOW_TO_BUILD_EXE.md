# Building CoachBoardTool.exe

This is for you, not for the coaches you're sending the tool to — they only
ever need the final `.exe` file (see "What to send coaches" at the bottom).

Windows executables have to be built on Windows — there's no way to produce
one from Mac/Linux. You've got two options below; **Option A needs no
Windows machine at all**, so start there unless you already have Windows
handy.

## Option A: GitHub Actions (no Windows machine needed)

This repo includes `.github/workflows/build-windows.yml`, which builds the
exe on a real (free) Windows machine that GitHub provides, automatically.

1. Push this folder to a GitHub repo (private is fine — Settings → set the
   repo to Private if you don't want it public).
2. Go to the repo's **Actions** tab. You should see "Build Windows exe" run
   automatically (it triggers on every push). If it hasn't started, click
   it in the sidebar, then **Run workflow**.
3. Wait for the green checkmark (2-4 minutes).
4. Click into the finished run → scroll to **Artifacts** →
   download **CoachBoardTool-windows**. That's a zip containing
   `CoachBoardTool.exe` — that's the file to send to coaches.

No Python, no PyInstaller, nothing to install locally for this path.

## Option B: Build it yourself on a Windows PC

If you have access to a Windows machine (yours, a colleague's, a VM):

1. Install Python 3.10+ from python.org (check "Add python.exe to PATH").
2. Open Command Prompt in this folder and run:
   ```
   pip install -r requirements.txt
   pip install pyinstaller
   ```
3. **Important** — pre-download ffmpeg so it gets bundled into the exe
   (otherwise coaches would need internet on first video export):
   ```
   python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
   ```
4. Build it:
   ```
   pyinstaller coach_board_tool.spec --noconfirm
   ```
5. The finished file is at `dist\CoachBoardTool.exe`. That's the file to
   send to coaches.

## What to send coaches

Just the one file: `CoachBoardTool.exe`. It's a single self-contained
program — no install, no Python, no ffmpeg setup on their end. They
double-click it and it opens.

It'll likely be 70-90 MB, which is too big for most email attachments —
share it via Google Drive, OneDrive, Dropbox, or WeTransfer instead.

**Windows SmartScreen note:** since this isn't a code-signed, widely-known
app, Windows will probably show a blue "Windows protected your PC" warning
the first time each coach runs it. They'll need to click **More info** →
**Run anyway**. Worth a heads-up in whatever message you send along with
the file, so it doesn't look like something's wrong.

**Where their data goes:** the exe creates `exports\` and `saved_plays\`
folders right next to itself the first time it needs them — so wherever a
coach puts the exe (Desktop, a folder, a USB stick) is where their clips
and saved plays will show up.

## Updating the exe later

Whenever the app's source changes, just repeat Option A or B — there's no
separate "update" step, you rebuild the whole exe and send the new file.
