# Design — Flaner (first iteration)

This document describes the design decisions and math used to convert between pixels and real-world units, which is critical to drawing the grid correctly.

Coordinate system

- The application uses screen/display pixels as the UI coordinate system.
- Images are displayed as pygame Surfaces. When the user clicks on the displayed image, the clicked coordinates are screen pixels.

Scale definition

The scale is defined by the user selecting two points on the displayed image and providing the real-world distance (in meters) between those two points.

- Let p1 = (x1, y1) and p2 = (x2, y2) be the two clicked points in screen pixels.
- Pixel distance: $d_p = \sqrt{(x2-x1)^2 + (y2-y1)^2}$
- If the user provides a real-world distance $D$ (in meters), then pixels-per-meter is:

$$
ppm = \frac{d_p}{D}
$$

Grid spacing

- The grid spacing is defined in meters (e.g., 0.50 m = 50 cm).
- Spacing in pixels is computed as:

$$
spacing_{px} = ppm \times spacing_{m}
$$

Rendering the grid

- The grid is drawn as vertical and horizontal lines across the display, spaced by `spacing_px`.
- Grid origin is aligned to the image top-left so coordinates on the grid map directly to the image coordinates.

UI choices

- Use `pygame` for rendering and main loop simplicity.
- Use `tkinter` file/dialog utilities to avoid reinventing file dialogs and text input boxes.

Notes and limitations

- Because the image may be scaled to fit the window, clicks and pixel calculations are performed on the displayed image coordinates. The computed `ppm` therefore corresponds to the displayed pixels, which is correct for on-screen measurement and printing at the same scale but would not directly map to the source file pixel density without extra bookkeeping.

