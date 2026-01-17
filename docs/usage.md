# Usage — Flaner (first iteration)

Quick start

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Run the app:

```bash
python src/flaner.py
```

Keys & interactions

- `O` — Open an image file dialog and load a plan/sketch/photo.
- `S` — Enter scale mode. Click two points on the image defining a known real-world distance, then enter that distance in meters when prompted.
- `G` — Change grid spacing (in centimeters) when prompted.
- `R` — Reset scale (clear the current scale).
- `Esc` — Quit the application.
 - `L` — Add a measurement line by dragging two points.
 - `D` — Add a rectangle by dragging two corners.
 - `Q` — Quicksave current project to the per-user `quicksave` folder (shows transient popup).
 - `K` — Open the projects folder in your system file browser.
 - `Delete` / `Backspace` — Delete the selected object.
 - `Ctrl+Z` / `Ctrl+Y` (`Ctrl+Shift+Z`) — Undo / Redo.

Mouse interactions

- Left-click inside the image to select an object. Drag the body to move it.
- Left-click near an endpoint (line) or corner (rectangle) and drag to resize that handle.
- Hold `Shift` while dragging to snap horizontal/vertical (lines) or force square resize (rectangles).
- Right-click inside the image to deselect.
- Middle-button drag shifts the grid offset.
- Mouse wheel zooms in/out centered on the cursor (wheel disabled while drawing).

Workflow example

1. Press `O` and pick a JPG/PNG of your flat sketch.
2. Press `S` and click the two endpoints corresponding to a measured length (e.g., a wall you measured with a tape measure).
3. Enter the real-world length in meters (e.g., `3.25`).
4. Press `G` to set grid granularity (e.g., `50` for 50 cm squares).
5. Inspect the grid overlay and repeat as needed.

