# Coach Board Tool

A desktop tool for drawing lacrosse plays and turning them into a short
animated clip (MP4 or GIF) you can drop straight into a PowerPoint slide.

Built with Python and Qt (PySide6). By [TCurrie11](https://github.com/TCurrie11).
See [CHANGELOG.md](CHANGELOG.md) for version history.

**Sending this to non-technical coaches?** They don't need any of the setup
below. See [HOW_TO_BUILD_EXE.md](HOW_TO_BUILD_EXE.md) to produce a
`CoachBoardTool.exe` (Windows) or `CoachBoardTool.app` (Mac) they can just
double-click.

## 1. Install

Requires Python 3.9+. From this folder:

```bash
pip install -r requirements.txt
```

Uses [PySide6](https://doc.qt.io/qtforpython-6/) (the official Qt for Python
bindings) for the window and anti-aliased drawing, plus `imageio` /
`imageio-ffmpeg` for video export. The first MP4 export silently downloads a
small ffmpeg binary. It needs internet once, then it's cached.

## 2. Run

```bash
python main.py
```

## 3. How it works

**Field.** Toggle *Half field* / *Full field* at any time. Both are drawn to
real field proportions (crease, goal, restraining line, attack area, wing
lines, sub box, coaches' area). The window resizes freely and the field
scales to fit.

**Rotation.** The 0° / 90° / 180° / 270° presets or the rotation box (any
angle; scroll or use the arrow keys to nudge by 15°) turn the whole scene
as one piece. Player letters stay upright. Whatever angle is set when you
export is baked into the video.

**Tools** (click the button or press the shortcut key):

| Tool | Key | What it does |
|---|---|---|
| Select | `V` | Drag any piece to reposition it. |
| Delete | `D` | Click a piece, line or pick to remove it. |
| Add X | `X` | Place an offensive player (red). |
| Add O | `O` | Place a defensive player (blue). |
| Ball | `B` | Place the ball; clicking again moves it. Its position carries into later steps. |
| Pick | `K` | Drop a pick / screen marker for this step. |
| Run | `A` | Draw a movement arrow freehand. Start it *on* a player and that player follows the curve when the play animates. |
| Pass | `P` | Draw a dashed pass line. Passes never move a player. |

Freehand lines are cleaned up when you let go: hand wobble is removed,
intended bends are kept, and a nearly straight drag snaps to a straight line.

**Line colour.** A line or pick that starts on a player takes that player's
colour. Otherwise it uses *Draw red* / *Draw blue*.

**Steps (the animation timeline).**
1. Place your starting formation and press **Add step** (`Ctrl+Enter`).
   Step 1 is just the starting positions.
2. Drag players to where they go next and draw runs / passes / picks.
3. Set **Move** (glide time) and **Hold** (pause once everyone's arrived).
4. Press **Add step** again. Repeat.
5. Select a step in the list to load its timing, edit it, then press
   **Apply timing**. **Delete step** removes the selected one.

**Undo.** `Ctrl+Z` undoes the last action in the step you're building.
*Edit → Remove last step* throws away the most recent committed step.

**Preview** (`F5`) plays the sequence on the board. Click or press `Esc` to
stop early.

**Export MP4 / GIF** (`Ctrl+E` / `Ctrl+Shift+E`) renders the animation at
1280×720 into an `exports/` folder next to the app, with a progress bar you
can cancel. MP4 goes into PowerPoint via *Insert → Video*. GIF is a
fallback (*Insert → Picture*).

**Save / Load play** (`Ctrl+S` / `Ctrl+O`) writes and reads a `.json` file in
a `saved_plays/` folder, using the name in the *File* box. Plays saved by
1.x open unchanged.

## 4. Project layout

| Module | Responsibility |
|---|---|
| `main.py` | Entry point; error logging and crash dialog. |
| `main_window.py` | Window, sidebar, menus and shortcuts; wires widgets to the editor. |
| `board_view.py` | The field widget: painting, mouse input, preview playback. |
| `editor.py` | `PlayEditor`: what each tool does, undo, steps. No UI code. |
| `scene.py` | Composes a frame and maps between screen and field coordinates. |
| `field.py` / `render.py` | QPainter drawing of the field and of pieces / lines. |
| `path_smoothing.py` | Freehand smoothing pipeline (pure geometry). |
| `timeline.py` | Steps and frame-by-frame interpolation. |
| `exporter.py` / `persistence.py` | Video export and JSON save / load. |
| `theme.py` / `icons.py` | Dark theme and runtime-drawn tool icons. |

## 5. Tests

```bash
python test_path_smoothing.py   # smoothing algorithm
python test_headless.py         # end-to-end: editor, window, rendering, export, save/load
```

Both run without a display (Qt's off-screen platform) and also work under
`pytest`. Test output goes to a temporary folder, never your real saves.

## 6. Notes / current limitations

- Switching Half ↔ Full field doesn't try to keep pieces in the same
  "logical" spot. It's a bigger canvas change, so nudge pieces after toggling.
- Deleting a step from the middle is safe but makes the jump into the next
  step larger, because each step stores absolute positions rather than deltas.
- If two movement arrows in the same step start on the same player, the
  later one wins.
