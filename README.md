# Coach Board Tool

A desktop tool for drawing lacrosse plays and turning them into a short
animated clip (MP4 or GIF) you can drop straight into a PowerPoint slide.

**Sending this to non-technical coaches?** They don't need any of the setup
below — see [HOW_TO_BUILD_EXE.md](HOW_TO_BUILD_EXE.md) to produce a
`CoachBoardTool.exe` (Windows) or `CoachBoardTool.app` (Mac) they can just
double-click.

The instructions below are for running it from source (e.g. while you're
still tweaking it).

## 1. Install

Requires Python 3.9+. From this folder:

```bash
pip install -r requirements.txt
```

Uses `pygame-ce` (the actively-maintained community fork of pygame — same
`import pygame`, but with pre-built wheels for newer Python versions) plus
`imageio`/`imageio-ffmpeg` for video export. The first MP4 export silently
downloads a small ffmpeg binary — needs internet once, then it's cached.

Optional sanity check before you dive in:

```bash
python test_headless.py
```

## 2. Run

```bash
python main.py
```

## 3. How it works

**Field** — toggle Half field / Full field any time. Both are drawn to real
field proportions (crease, goal, restraining line, attack area, wing lines,
sub box, coaches area).

**Rotate field** — the four preset buttons (0°/90°/180°/270°) or the free
text box below them (any angle, negative allowed) spin the whole scene —
field, players, arrows, everything — as one piece. Whatever angle is set
when you export is baked into the MP4/GIF too.

**Tools** (left click on the field):
- **Select / Move** — click and drag any piece to reposition it.
- **Add X (offense, red)** / **Add O (defense, blue)** — click an empty
  spot to drop a new piece.
- **Add ball** — click to place the ball (bright orange). Clicking again
  moves the existing ball rather than adding a second one. Its position
  carries forward into new steps automatically, same as any piece, until
  you drag it somewhere else.
- **Arrow (move)** — click and drag freehand; released, it's automatically
  smoothed into a clean curve. If you start the drag *on* a piece, that
  piece will glide along this exact curve when the play animates - draw it
  the way the run actually bends.
- **Dotted (pass)** — same freehand-smoothing, dashed instead of solid.
  Passes are never followed by a piece — they represent the ball, not a
  run, even if drawn starting on one.
- **Triangle (pick)** — click a spot to drop a pick/screen marker. Picks
  are transient like arrows/passes — visible only during the step they're
  drawn in, not for the rest of the play.
- **Delete** — click a piece, arrow, pass, or pick to remove it.

**Color of arrows/passes/picks:** start the click-drag *on* a piece and the
line automatically takes that piece's color. Start on open grass and it
uses whichever "Draw: Red / Draw: Blue" toggle is active.

**Undo:**
- **Undo last action** — steps back through your in-progress edits in the
  *current* frame (placing a piece, moving one, drawing an arrow, etc.),
  one at a time. Resets once you commit a step.
- **Undo last step** — throws away the entire most-recently-committed step.

**Steps (the animation timeline):**
1. Place your starting formation, click **Add Step** (Step 1: no movement,
   just starting positions).
2. Drag pieces to where they go next, draw arrows/passes/picks to show how.
   Draw a piece's movement arrow *starting on that piece* if you want it to
   trace the curve rather than beeline to its new spot.
3. Set **Move (s)** (glide duration — fast cut vs. slow drift) and
   **Hold (s)** (pause once everyone's arrived).
4. Click **Add Step** again. Repeat.
5. Click a step in the list to reload its timing for editing, then
   **Update selected step timing**. The "x" next to a step deletes it.

**Preview** plays the sequence in-app (click or Esc to stop early).

**Export MP4 / Export GIF** renders the full animation, at whatever field
rotation is currently set, and saves it into an `exports/` folder created
next to the app, using the name in the box below. MP4 → PowerPoint via
Insert → Video. GIF is there as a fallback (Insert → Picture).

**Save play / Load play** writes/reads a `.json` file into a `saved_plays/`
folder (also auto-created), using that same name box.

## 4. Notes / current limitations

- Fixed 1300x800 window — not resizable in this version.
- Switching Half field <-> Full field doesn't try to preserve where pieces
  "logically" sit - it's a bigger canvas change, so nudge pieces after
  toggling.
- Deleting a step from the middle of the sequence is safe but will make the
  jump into the next step larger, since each step stores absolute
  positions rather than deltas.
- If two movement arrows in the same step both start on the same piece,
  the later one wins.
