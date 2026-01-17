import math
import sys
import os
import json
import shutil
import pygame
import subprocess
from objects.scale_line import ScaleLine
from objects.measure_line import MeasureLine
from objects.rectangle import Rectangle
import tkinter as tk
from tkinter import filedialog, simpledialog

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
BG_COLOR = (30, 30, 30)
SIDEBAR_COLOR = (40, 40, 40)
GRID_COLOR = (0, 200, 200)
SCALE_COLOR = (255, 100, 100)
TEXT_COLOR = (230, 230, 230)
SIDEBAR_WIDTH = 300
TEXT_PADDING = 4


def get_projects_root():
    """Return the projects root folder.

    Priority order:
    - Environment variable `FLANER_PROJECTS` (if set)
    - On Windows: `~/Documents/Flaner/projects` (user-accessible)
    - On other OS: XDG_DATA_HOME or ~/.local/share/Flaner/projects
    If creation fails, fall back to a `projects` folder in the current working dir.
    """
    try:
        # allow overriding the location for portability/debugging
        env = os.getenv('FLANER_PROJECTS')
        if env:
            root = env
        elif os.name == 'nt':
            # prefer Documents so the folder is easy to open in Explorer
            docs = os.path.join(os.path.expanduser('~'), 'Documents')
            root = os.path.join(docs, 'Flaner', 'projects')
        else:
            # use XDG data home or fallback to ~/.local/share
            xdg = os.getenv('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
            root = os.path.join(xdg, 'Flaner', 'projects')

        os.makedirs(root, exist_ok=True)
        return root
    except Exception:
        # final fallback to cwd/projects
        fallback = os.path.join(os.getcwd(), 'projects')
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

def open_image_dialog():
    # create a temporary hidden tkinter root to own the dialog
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Open image",
        filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*")]
    )
    try:
        root.destroy()
    except Exception:
        pass
    if not path:
        return None
    try:
        img = pygame.image.load(path)
        return img
    except Exception as e:
        print("Failed to load image:", e)
        return None

def ask_float(prompt, title="Input", initial=0.0):
    try:
        root = tk.Tk()
        root.withdraw()
        val = simpledialog.askfloat(title, prompt, initialvalue=initial)
        try:
            root.destroy()
        except Exception:
            pass
        return val
    except Exception:
        return None

def draw_text(surface, text, pos, font, color=TEXT_COLOR):
    lines = text.split('\n')
    x, y = pos
    for i, line in enumerate(lines):
        img = font.render(line, True, color)
        surface.blit(img, (x, y + i * (font.get_linesize())))

def scale_image_to_area(original, area_w, area_h):
    iw, ih = original.get_size()
    scale = min(area_w / iw, area_h / ih, 1.0)
    display_w = max(1, int(iw * scale))
    display_h = max(1, int(ih * scale))
    return pygame.transform.smoothscale(original, (display_w, display_h))


def _norm(vx, vy):
    d = math.hypot(vx, vy)
    if d == 0:
        return 0.0, 0.0
    return vx / d, vy / d


def draw_perp_cap(surface, p1, p2, color, length=8, width=3):
    # draw a short perpendicular cap at p1 and p2
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    nx, ny = _norm(dx, dy)
    # perpendicular
    px, py = -ny, nx
    lx = int(length * px)
    ly = int(length * py)
    try:
        pygame.draw.line(surface, color, (int(x1 - lx), int(y1 - ly)), (int(x1 + lx), int(y1 + ly)), width)
        pygame.draw.line(surface, color, (int(x2 - lx), int(y2 - ly)), (int(x2 + lx), int(y2 + ly)), width)
    except Exception:
        pygame.draw.line(surface, color, (int(x1 - lx), int(y1 - ly)), (int(x1 + lx), int(y1 + ly)), width)


def draw_arrow_ends(surface, p1, p2, color, size=10, width=2):
    # draw simple arrowheads at both ends pointing outwards
    x1, y1 = p1
    x2, y2 = p2
    # arrow at p1 pointing outward (direction p1 - p2)
    try:
        ang1 = math.atan2(y1 - y2, x1 - x2)
        left1 = (int(x1 - size * math.cos(ang1 - math.pi/6)), int(y1 - size * math.sin(ang1 - math.pi/6)))
        right1 = (int(x1 - size * math.cos(ang1 + math.pi/6)), int(y1 - size * math.sin(ang1 + math.pi/6)))
        pygame.draw.polygon(surface, color, [(int(x1), int(y1)), left1, right1])
        # arrow at p2 pointing outward (direction p2 - p1)
        ang2 = math.atan2(y2 - y1, x2 - x1)
        left2 = (int(x2 - size * math.cos(ang2 - math.pi/6)), int(y2 - size * math.sin(ang2 - math.pi/6)))
        right2 = (int(x2 - size * math.cos(ang2 + math.pi/6)), int(y2 - size * math.sin(ang2 + math.pi/6)))
        pygame.draw.polygon(surface, color, [(int(x2), int(y2)), left2, right2])
    except Exception:
        pass

def main():
    pygame.init()
    # pygame initialized
    win_w, win_h = WINDOW_WIDTH, WINDOW_HEIGHT
    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    pygame.display.set_caption("Flaner — Flat planner")
    clock = pygame.time.Clock()
    # display created
    font = pygame.font.SysFont(None, 20)
    sidebar_font = pygame.font.SysFont(None, 24)

    image = None
    original_image = None
    image_path = None
    image_rect = pygame.Rect(0, 0, 0, 0)
    orig_w = orig_h = 0
    image_scale = 1.0
    user_zoomed = False
    panning = False
    pan_start = (0, 0)
    image_start_pos = (0, 0)
    grid_visible = True
    # line width for drawable objects
    object_line_width = 2
    SLIDER_MIN = 1
    SLIDER_MAX = 12
    slider_dragging = False
    slider_rect = None
    # label size slider
    label_scale = 1.0
    LABEL_SCALE_MIN = 0.5
    LABEL_SCALE_MAX = 3.0
    label_slider_dragging = False
    label_slider_rect = None
    # grid offset (pixels) for manual adjustment via middle-mouse drag
    grid_offset_px = [0.0, 0.0]
    grid_dragging = False
    grid_drag_start = (0, 0)
    grid_offset_start = (0.0, 0.0)
    drawing = False
    draw_start = (0, 0)
    draw_current = (0, 0)
    # object model
    scale_object = None  # only one scale allowed
    objects = []  # other drawable objects (MeasureLine instances etc.)
    selected_obj = None
    obj_dragging = False
    obj_drag_last = (0, 0)
    resize_mode = False
    resize_handle = None
    resize_anchor_screen = None
    # undo/redo stacks store snapshots of (scale_object, objects)
    import copy
    undo_stack = []
    redo_stack = []
    UNDO_LIMIT = 100

    def snapshot_state():
        return (copy.deepcopy(scale_object), copy.deepcopy(objects))

    def restore_snapshot(snap):
        nonlocal scale_object, objects, pixels_per_meter, selected_obj
        so, objs = snap
        scale_object = copy.deepcopy(so)
        objects = copy.deepcopy(objs)
        # recompute derived value
        try:
            pixels_per_meter = scale_object.pixels_per_meter if scale_object else None
        except Exception:
            pixels_per_meter = None
        selected_obj = None

    def push_undo():
        nonlocal undo_stack, redo_stack
        try:
            undo_stack.append(snapshot_state())
            if len(undo_stack) > UNDO_LIMIT:
                undo_stack.pop(0)
            redo_stack.clear()
        except Exception:
            pass

    def do_undo():
        nonlocal undo_stack, redo_stack
        try:
            if not undo_stack:
                return
            # push current to redo
            redo_stack.append(snapshot_state())
            snap = undo_stack.pop()
            restore_snapshot(snap)
        except Exception:
            pass

    def do_redo():
        nonlocal undo_stack, redo_stack
        try:
            if not redo_stack:
                return
            undo_stack.append(snapshot_state())
            snap = redo_stack.pop()
            restore_snapshot(snap)
        except Exception:
            pass

    running = True

    mode = 'normal'  # 'setting_scale' or 'add_measure'
    # add_rect mode for rectangle creation
    # trigger with key 'D'
    scale_points = []
    pixels_per_meter = None
    grid_spacing_m = 0.5  # default 50 cm
    # quicksave popup state (milliseconds since pygame start)
    quicksave_popup_until = 0
    quicksave_msg = ""
    
    frame_count = 0
    while running:
        # poll events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                win_w, win_h = event.w, event.h
                screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
                # rescale the image to fit the new area (if present)
                if original_image:
                    orig_w, orig_h = original_image.get_size()
                    area_w = max(1, win_w - SIDEBAR_WIDTH)
                    area_h = max(1, win_h)
                    if not user_zoomed:
                        image_scale = min(area_w / orig_w, area_h / orig_h, 1.0)
                    new_w = max(1, int(orig_w * image_scale))
                    new_h = max(1, int(orig_h * image_scale))
                    image = pygame.transform.smoothscale(original_image, (new_w, new_h))
                    image_rect = pygame.Rect(SIDEBAR_WIDTH, 0, new_w, new_h)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_o:
                    path = filedialog.askopenfilename(
                        title="Open image",
                        filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*")]
                    )
                    if path:
                        try:
                            original_image = pygame.image.load(path).convert_alpha()
                            image_path = path
                            orig_w, orig_h = original_image.get_size()
                            area_w = max(1, win_w - SIDEBAR_WIDTH)
                            area_h = max(1, win_h)
                            image_scale = min(area_w / orig_w, area_h / orig_h, 1.0)
                            user_zoomed = False
                            new_w = max(1, int(orig_w * image_scale))
                            new_h = max(1, int(orig_h * image_scale))
                            image = pygame.transform.smoothscale(original_image, (new_w, new_h))
                            image_rect = pygame.Rect(SIDEBAR_WIDTH, 0, new_w, new_h)
                        except Exception as e:
                            print("Failed to load image:", e)
                elif event.key == pygame.K_s:
                    if image:
                        mode = 'setting_scale'
                        scale_points = []
                # Undo/redo shortcuts
                mods = pygame.key.get_mods()
                if event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
                    if mods & pygame.KMOD_SHIFT:
                        do_redo()
                    else:
                        do_undo()
                elif event.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
                    do_redo()
                elif event.key == pygame.K_l:
                    if image:
                        mode = 'add_measure'
                        scale_points = []
                elif event.key == pygame.K_d:
                    if image:
                        mode = 'add_rect'
                        scale_points = []
                elif event.key == pygame.K_c:
                    # cancel drawing mode
                    if mode in ('setting_scale', 'add_measure', 'add_rect'):
                        mode = 'normal'
                        drawing = False
                        scale_points = []
                elif event.key == pygame.K_p:
                    # save project to per-user projects folder
                    if original_image and image_path:
                        name = simpledialog.askstring("Save project", "Project name:")
                        if name:
                            root_projects = get_projects_root()
                            proj_dir = os.path.join(root_projects, name)
                            os.makedirs(proj_dir, exist_ok=True)
                            img_name = os.path.basename(image_path)
                            dst_img = os.path.join(proj_dir, img_name)
                            try:
                                shutil.copy(image_path, dst_img)
                            except Exception as e:
                                print("Failed to copy image:", e)
                            j = {"image": img_name, "objects": []}
                            if scale_object:
                                j["objects"].append(scale_object.to_dict())
                            for o in objects:
                                j["objects"].append(o.to_dict())
                            with open(os.path.join(proj_dir, "project.json"), "w", encoding="utf-8") as fh:
                                json.dump(j, fh, indent=2)
                elif event.key == pygame.K_q:
                    # Quicksave OR quickload: if nothing is open (no image, no scale, no objects), try to load quicksave.
                    try:
                        root_projects = get_projects_root()
                        quick_dir = os.path.join(root_projects, 'quicksave')
                        pj = os.path.join(quick_dir, 'project.json')
                        if (not original_image) and (scale_object is None) and (len(objects) == 0):
                            # attempt to load quicksave
                            if os.path.exists(pj):
                                try:
                                    with open(pj, 'r', encoding='utf-8') as fh:
                                        data = json.load(fh)
                                    img_file = os.path.join(quick_dir, data.get('image'))
                                    if os.path.exists(img_file):
                                        image_path = img_file
                                        original_image = pygame.image.load(img_file).convert_alpha()
                                        orig_w, orig_h = original_image.get_size()
                                        area_w = max(1, win_w - SIDEBAR_WIDTH)
                                        area_h = max(1, win_h)
                                        image_scale = min(area_w / orig_w, area_h / orig_h, 1.0)
                                        user_zoomed = False
                                        new_w = max(1, int(orig_w * image_scale))
                                        new_h = max(1, int(orig_h * image_scale))
                                        image = pygame.transform.smoothscale(original_image, (new_w, new_h))
                                        image_rect = pygame.Rect(SIDEBAR_WIDTH, 0, new_w, new_h)
                                    # rebuild objects
                                    scale_object = None
                                    objects = []
                                    for it in data.get('objects', []):
                                        if it.get('type') == 'scale':
                                            p1 = tuple(it.get('p1'))
                                            p2 = tuple(it.get('p2'))
                                            m = it.get('meters')
                                            w = int(it.get('width', object_line_width))
                                            scale_object = ScaleLine(p1, p2, m, width=w)
                                            pixels_per_meter = scale_object.pixels_per_meter
                                        elif it.get('type') == 'measure':
                                            p1 = tuple(it.get('p1'))
                                            p2 = tuple(it.get('p2'))
                                            m = it.get('meters')
                                            w = int(it.get('width', object_line_width))
                                            objects.append(MeasureLine(p1, p2, m, width=w))
                                        elif it.get('type') == 'rect':
                                            try:
                                                objects.append(Rectangle.from_dict(it))
                                            except Exception:
                                                pass
                                    # clear and seed undo/redo
                                    try:
                                        undo_stack.clear()
                                        redo_stack.clear()
                                        push_undo()
                                    except Exception:
                                        pass
                                    quicksave_msg = f"Loaded quicksave from {quick_dir}"
                                    try:
                                        quicksave_popup_until = pygame.time.get_ticks() + 2000
                                    except Exception:
                                        quicksave_popup_until = 0
                                except Exception as e_l:
                                    print('Failed to load quicksave project:', e_l)
                            else:
                                print('No quicksave found at', pj)
                        else:
                            # perform quicksave
                            if original_image and image_path:
                                try:
                                    os.makedirs(quick_dir, exist_ok=True)
                                    img_name = os.path.basename(image_path)
                                    dst_img = os.path.join(quick_dir, img_name)
                                    try:
                                        src_ab = os.path.abspath(image_path)
                                        dst_ab = os.path.abspath(dst_img)
                                        if src_ab.lower() != dst_ab.lower():
                                            shutil.copy(image_path, dst_img)
                                    except Exception as e_copy:
                                        print('Quicksave: failed to copy image:', e_copy)
                                    j = {'image': img_name, 'objects': []}
                                    if scale_object:
                                        j['objects'].append(scale_object.to_dict())
                                    for o in objects:
                                        j['objects'].append(o.to_dict())
                                    with open(os.path.join(quick_dir, 'project.json'), 'w', encoding='utf-8') as fh:
                                        json.dump(j, fh, indent=2)
                                    quicksave_msg = f"Quicksaved to {quick_dir}"
                                    try:
                                        quicksave_popup_until = pygame.time.get_ticks() + 2000
                                    except Exception:
                                        quicksave_popup_until = 0
                                except Exception as e_qs:
                                    print('Quicksave failed:', e_qs)
                    except Exception as e_q:
                        print('Quicksave handling failed:', e_q)
                elif event.key == pygame.K_j:
                    # load project folder (default to per-user projects folder)
                    try:
                        d = filedialog.askdirectory(title="Open project folder", initialdir=get_projects_root())
                    except Exception:
                        d = filedialog.askdirectory(title="Open project folder")
                    if d:
                        pj = os.path.join(d, "project.json")
                        try:
                            with open(pj, "r", encoding="utf-8") as fh:
                                data = json.load(fh)
                            img_file = os.path.join(d, data.get("image"))
                            if os.path.exists(img_file):
                                image_path = img_file
                                original_image = pygame.image.load(img_file).convert_alpha()
                                orig_w, orig_h = original_image.get_size()
                                area_w = max(1, win_w - SIDEBAR_WIDTH)
                                area_h = max(1, win_h)
                                image_scale = min(area_w / orig_w, area_h / orig_h, 1.0)
                                user_zoomed = False
                                new_w = max(1, int(orig_w * image_scale))
                                new_h = max(1, int(orig_h * image_scale))
                                image = pygame.transform.smoothscale(original_image, (new_w, new_h))
                                image_rect = pygame.Rect(SIDEBAR_WIDTH, 0, new_w, new_h)
                            # rebuild objects
                            scale_object = None
                            objects = []
                            for it in data.get("objects", []):
                                if it.get("type") == "scale":
                                    p1 = tuple(it.get("p1"))
                                    p2 = tuple(it.get("p2"))
                                    m = it.get("meters")
                                    w = int(it.get('width', object_line_width))
                                    scale_object = ScaleLine(p1, p2, m, width=w)
                                    pixels_per_meter = scale_object.pixels_per_meter
                                elif it.get("type") == "measure":
                                    p1 = tuple(it.get("p1"))
                                    p2 = tuple(it.get("p2"))
                                    m = it.get("meters")
                                    w = int(it.get('width', object_line_width))
                                    objects.append(MeasureLine(p1, p2, m, width=w))
                                elif it.get("type") == "rect":
                                    try:
                                        objects.append(Rectangle.from_dict(it))
                                    except Exception:
                                        pass
                            # clear undo/redo history on load
                            try:
                                undo_stack.clear()
                                redo_stack.clear()
                                push_undo()
                            except Exception:
                                pass
                        except Exception as e:
                            print("Failed to load project:", e)
                elif event.key == pygame.K_g:
                    val = ask_float("Enter grid spacing in centimeters:", "Grid spacing", initial=50.0)
                    if val and val > 0:
                        grid_spacing_m = val / 100.0
                elif event.key == pygame.K_v:
                    grid_visible = not grid_visible
                elif event.key == pygame.K_r:
                    pixels_per_meter = None
                    scale_object = None
                    scale_points = []
                elif event.key == pygame.K_k:
                    # open the projects folder in the system file browser
                    try:
                        proj_root = get_projects_root()
                        # ensure folder exists (get_projects_root should have created it,
                        # but try again to be safe and detect errors early)
                        try:
                            os.makedirs(proj_root, exist_ok=True)
                        except Exception as e_mk:
                            # Cannot create the intended projects folder. Offer a local fallback.
                            fallback = os.path.join(os.getcwd(), 'projects')
                            try:
                                os.makedirs(fallback, exist_ok=True)
                            except Exception:
                                pass
                            try:
                                rt = tk.Tk(); rt.withdraw()
                                import tkinter.messagebox as _mb
                                resp = _mb.askyesno("Open Projects", f"The configured projects folder:\n{proj_root}\n\nis not accessible (error creating it).\nOpen a local fallback folder instead?\n\nYou can copy the path from this dialog.")
                                rt.destroy()
                            except Exception:
                                resp = False
                            if resp:
                                try:
                                    if os.name == 'nt':
                                        os.startfile(fallback)
                                    elif sys.platform == 'darwin':
                                        subprocess.run(['open', fallback])
                                    else:
                                        subprocess.run(['xdg-open', fallback])
                                except Exception:
                                    try:
                                        subprocess.run(['explorer', fallback])
                                    except Exception:
                                        print('Failed to open fallback projects folder:', fallback)
                            else:
                                print('Projects folder not available and user declined fallback.')
                            continue

                        # verify we can access the folder (listing it); if not, ask user to open fallback
                        try:
                            _ = os.listdir(proj_root)
                        except Exception as e_list:
                            fallback = os.path.join(os.getcwd(), 'projects')
                            try:
                                os.makedirs(fallback, exist_ok=True)
                            except Exception:
                                pass
                            try:
                                rt = tk.Tk(); rt.withdraw()
                                import tkinter.messagebox as _mb
                                resp = _mb.askyesno("Open Projects", f"The configured projects folder:\n{proj_root}\n\nappears to be unavailable:\n{e_list}\n\nOpen a local fallback folder instead?")
                                rt.destroy()
                            except Exception:
                                resp = False
                            if resp:
                                try:
                                    if os.name == 'nt':
                                        os.startfile(fallback)
                                    elif sys.platform == 'darwin':
                                        subprocess.run(['open', fallback])
                                    else:
                                        subprocess.run(['xdg-open', fallback])
                                except Exception:
                                    try:
                                        subprocess.run(['explorer', fallback])
                                    except Exception:
                                        print('Failed to open fallback projects folder:', fallback)
                            else:
                                print('Projects folder not accessible and user declined fallback.')
                            continue

                        # folder exists and is listable — open it
                        if os.name == 'nt':
                            try:
                                os.startfile(proj_root)
                            except Exception:
                                try:
                                    subprocess.run(['explorer', proj_root])
                                except Exception as e2:
                                    print('Failed to open projects folder with explorer:', e2)
                        else:
                            if sys.platform == 'darwin':
                                subprocess.run(['open', proj_root])
                            else:
                                subprocess.run(['xdg-open', proj_root])
                    except Exception as e:
                        print('Failed to open projects folder:', e)
                elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    # delete selected object
                    if selected_obj:
                        push_undo()
                        try:
                            if selected_obj is scale_object:
                                scale_object = None
                                pixels_per_meter = None
                            else:
                                objects.remove(selected_obj)
                        except Exception:
                            pass
                        selected_obj = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # mouse wheel handled by MOUSEWHEEL event
                # clickable sidebar cancel button
                if event.button == 1:
                    sx, sy = event.pos
                    if sx < SIDEBAR_WIDTH:
                        cancel_rect = pygame.Rect(10, 120, SIDEBAR_WIDTH - 20, 30)
                        if mode in ('setting_scale', 'add_measure', 'add_rect') and cancel_rect.collidepoint((sx, sy)):
                            mode = 'normal'
                            drawing = False
                            scale_points = []
                            continue
                        # slider click handling (line width and label size sliders)
                        if slider_rect and slider_rect.collidepoint((sx, sy)):
                            slider_dragging = True
                            continue
                        if label_slider_rect and label_slider_rect.collidepoint((sx, sy)):
                            label_slider_dragging = True
                            continue
                if event.button == 1 and image and mode == 'normal':
                    mx, my = event.pos
                    if image_rect.inflate(2,2).collidepoint(mx, my):
                        # first check for object selection (top-most first)
                        found = None
                        # check scale object
                        try:
                            if scale_object and scale_object.hit_test(mx, my, image_rect, image_scale):
                                found = scale_object
                        except Exception:
                            found = None
                        # check other objects (reverse order so top-most selected)
                        if not found:
                            for o in reversed(objects):
                                try:
                                    if hasattr(o, 'hit_test') and o.hit_test(mx, my, image_rect, image_scale):
                                        found = o
                                        break
                                except Exception:
                                    continue
                        if found:
                            # record current state for undo before any mutation
                            push_undo()
                            # check if user clicked a handle first
                            handle_idx = None
                            try:
                                if hasattr(found, 'hit_test_handle'):
                                    handle_idx = found.hit_test_handle(mx, my, image_rect, image_scale)
                            except Exception:
                                handle_idx = None
                            selected_obj = found
                            if handle_idx is not None:
                                resize_mode = True
                                resize_handle = handle_idx
                                obj_drag_last = (mx, my)
                                # compute anchor screen coords (opposite point)
                                try:
                                    if hasattr(found, 'p1') and hasattr(found, 'p2'):
                                        # For rectangles, p1/p2 ordering may be arbitrary; compute canonical opposite corner
                                        if isinstance(found, Rectangle):
                                            x1o, y1o = found.p1
                                            x2o, y2o = found.p2
                                            xmin = min(x1o, x2o)
                                            xmax = max(x1o, x2o)
                                            ymin = min(y1o, y2o)
                                            ymax = max(y1o, y2o)
                                            if handle_idx == 0:
                                                anchor_orig = (xmax, ymax)
                                            elif handle_idx == 1:
                                                anchor_orig = (xmin, ymax)
                                            elif handle_idx == 2:
                                                anchor_orig = (xmax, ymin)
                                            else:
                                                anchor_orig = (xmin, ymin)
                                        else:
                                            # line-like objects: opposite endpoint
                                            if handle_idx == 0:
                                                anchor_orig = found.p2
                                            else:
                                                anchor_orig = found.p1
                                        resize_anchor_screen = (int(image_rect.x + anchor_orig[0] * image_scale), int(image_rect.y + anchor_orig[1] * image_scale))
                                    else:
                                        resize_anchor_screen = None
                                except Exception:
                                    resize_anchor_screen = None
                            else:
                                obj_dragging = True
                                obj_drag_last = (mx, my)
                        else:
                            # click on blank image -> deselect
                            selected_obj = None
                            # start panning
                            panning = True
                            pan_start = (mx, my)
                            image_start_pos = image_rect.topleft
                # middle mouse to drag grid offset
                if event.button == 2 and image and grid_visible:
                    grid_dragging = True
                    grid_drag_start = event.pos
                    grid_offset_start = (grid_offset_px[0], grid_offset_px[1])
                # right-click deselect
                if event.button == 3 and image and mode == 'normal':
                    mx, my = event.pos
                    if image_rect.inflate(2,2).collidepoint(mx, my):
                        selected_obj = None
                # start drawing a scale/measure line by drag
                if event.button == 1 and image and mode in ('setting_scale', 'add_measure', 'add_rect'):
                    mx, my = event.pos
                    if image_rect.inflate(2,2).collidepoint(mx, my):
                        # push undo before starting a new drawn object
                        push_undo()
                        drawing = True
                        draw_start = (mx, my)
                        draw_current = (mx, my)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    # finish panning
                    if panning:
                        panning = False
                    # finish object dragging / resizing
                    if obj_dragging:
                        obj_dragging = False
                    if resize_mode:
                        resize_mode = False
                        resize_handle = None
                    # finish drawing (scale or measure)
                    if 'drawing' in locals() and drawing and image and mode in ('setting_scale', 'add_measure', 'add_rect'):
                        sx1, sy1 = draw_start
                        sx2, sy2 = draw_current
                        # if shift held at release and adding rect, enforce square
                        try:
                            if mode == 'add_rect' and (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                                dx = sx2 - sx1
                                dy = sy2 - sy1
                                size = max(abs(dx), abs(dy))
                                sx2 = sx1 + (size if dx >= 0 else -size)
                                sy2 = sy1 + (size if dy >= 0 else -size)
                        except Exception:
                            pass
                        if image_rect.collidepoint(sx2, sy2):
                            ox1 = (sx1 - image_rect.x) / image_scale
                            oy1 = (sy1 - image_rect.y) / image_scale
                            ox2 = (sx2 - image_rect.x) / image_scale
                            oy2 = (sy2 - image_rect.y) / image_scale
                            if mode == 'setting_scale':
                                # ask for real-world distance for scale
                                val = ask_float("Enter real-world distance between the two points (meters):", "Set scale", initial=1.0)
                                if val and val > 0:
                                    scale_object = ScaleLine((ox1, oy1), (ox2, oy2), val, width=object_line_width)
                                    pixels_per_meter = scale_object.pixels_per_meter
                            elif mode == 'add_rect':
                                try:
                                    rect_obj = Rectangle((ox1, oy1), (ox2, oy2), width=object_line_width)
                                    objects.append(rect_obj)
                                except Exception:
                                    pass
                            else:
                                # automatically compute measurement from current scale (no dialog)
                                dp = math.hypot(ox2-ox1, oy2-oy1)
                                if pixels_per_meter:
                                    meters = round(dp / pixels_per_meter, 2)
                                else:
                                    meters = None
                                try:
                                    ml = MeasureLine((ox1, oy1), (ox2, oy2), meters, width=object_line_width)
                                    objects.append(ml)
                                except Exception:
                                    pass
                        mode = 'normal'
                        drawing = False
                if event.button == 2:
                    grid_dragging = False
                if event.button == 1:
                    # release slider drag
                    slider_dragging = False
                    label_slider_dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if resize_mode and selected_obj and image:
                    mx, my = event.pos
                    # determine target screen position, applying Shift-based snapping
                    tx, ty = mx, my
                    mods = pygame.key.get_mods()
                    try:
                        if mods & pygame.KMOD_SHIFT and resize_anchor_screen is not None:
                            ax, ay = resize_anchor_screen
                            # line endpoints: snap horizontal/vertical based on dominant delta
                            if isinstance(selected_obj, MeasureLine) or isinstance(selected_obj, ScaleLine):
                                dxs = mx - ax
                                dys = my - ay
                                if abs(dxs) > abs(dys):
                                    ty = ay
                                else:
                                    tx = ax
                            else:
                                # rectangle: enforce square while resizing
                                dxs = mx - ax
                                dys = my - ay
                                sx = 1 if dxs >= 0 else -1
                                sy = 1 if dys >= 0 else -1
                                size = max(abs(dxs), abs(dys))
                                tx = int(ax + sx * size)
                                ty = int(ay + sy * size)
                    except Exception:
                        tx, ty = mx, my
                    # convert target to original-image coords
                    if image_scale != 0:
                        tox = (tx - image_rect.x) / image_scale
                        toy = (ty - image_rect.y) / image_scale
                        # current handle original coords
                        try:
                            # determine current handle position in original-image coords
                            if isinstance(selected_obj, Rectangle):
                                x1o, y1o = selected_obj.p1
                                x2o, y2o = selected_obj.p2
                                xmin = min(x1o, x2o)
                                xmax = max(x1o, x2o)
                                ymin = min(y1o, y2o)
                                ymax = max(y1o, y2o)
                                if resize_handle == 0:
                                    curx, cury = xmin, ymin
                                elif resize_handle == 1:
                                    curx, cury = xmax, ymin
                                elif resize_handle == 2:
                                    curx, cury = xmin, ymax
                                else:
                                    curx, cury = xmax, ymax
                            else:
                                if resize_handle == 0:
                                    curx, cury = selected_obj.p1
                                else:
                                    curx, cury = selected_obj.p2
                            dxo = tox - curx
                            dyo = toy - cury
                            try:
                                selected_obj.move_handle(resize_handle, dxo, dyo)
                            except Exception:
                                pass
                        except Exception:
                            pass
                    obj_drag_last = (mx, my)
                if obj_dragging and selected_obj and image:
                    mx, my = event.pos
                    dx = mx - obj_drag_last[0]
                    dy = my - obj_drag_last[1]
                    # convert screen delta to original-image pixels
                    if image_scale != 0:
                        dxo = dx / image_scale
                        dyo = dy / image_scale
                        try:
                            selected_obj.move_by(dxo, dyo)
                        except Exception:
                            pass
                    obj_drag_last = (mx, my)
                if panning and image:
                    mx, my = event.pos
                    dx = mx - pan_start[0]
                    dy = my - pan_start[1]
                    image_rect.topleft = (image_start_pos[0] + dx, image_start_pos[1] + dy)
                if grid_dragging:
                    mx, my = event.pos
                    dx = mx - grid_drag_start[0]
                    dy = my - grid_drag_start[1]
                    grid_offset_px[0] = grid_offset_start[0] + dx
                    grid_offset_px[1] = grid_offset_start[1] + dy
                if 'drawing' in locals() and drawing:
                    mx, my = event.pos
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        # If adding rectangle, make it a square (lock width==height)
                        if mode == 'add_rect':
                            dx = mx - draw_start[0]
                            dy = my - draw_start[1]
                            size = max(abs(dx), abs(dy))
                            sx = draw_start[0] + (size if dx >= 0 else -size)
                            sy = draw_start[1] + (size if dy >= 0 else -size)
                            mx, my = sx, sy
                        else:
                            dx = mx - draw_start[0]
                            dy = my - draw_start[1]
                            if abs(dx) > abs(dy):
                                # snap horizontal
                                my = draw_start[1]
                            else:
                                # snap vertical
                                mx = draw_start[0]
                    draw_current = (mx, my)
                # handle slider dragging
                if slider_dragging:
                    sx, sy = event.pos
                    if slider_rect:
                        tx, ty, tw, th = slider_rect
                        rel = (sx - tx) / float(tw)
                        rel = max(0.0, min(1.0, rel))
                        new_w = int(round(SLIDER_MIN + rel * (SLIDER_MAX - SLIDER_MIN)))
                        if new_w != object_line_width:
                            object_line_width = new_w
                            # apply to existing objects
                            if scale_object is not None:
                                try:
                                    scale_object.width = object_line_width
                                except Exception:
                                    pass
                            for o in objects:
                                try:
                                    o.width = object_line_width
                                except Exception:
                                    setattr(o, 'width', object_line_width)
                if label_slider_dragging:
                    sx, sy = event.pos
                    if label_slider_rect:
                        tx, ty, tw, th = label_slider_rect
                        rel = (sx - tx) / float(tw)
                        rel = max(0.0, min(1.0, rel))
                        new_scale = (LABEL_SCALE_MIN + rel * (LABEL_SCALE_MAX - LABEL_SCALE_MIN))
                        if abs(new_scale - label_scale) > 1e-3:
                            label_scale = new_scale
            elif event.type == pygame.MOUSEWHEEL:
                # zoom in/out with wheel, centered on mouse
                # Ignore zoom while actively drawing (prevent accidental extreme zoom)
                if 'drawing' in locals() and drawing:
                    # skip zoom events during drawing modes
                    continue
                if image:
                    # determine zoom factor
                    factor = 1.1 ** event.y
                    # clamp
                    new_scale = max(0.05, min(image_scale * factor, 10.0))
                    if abs(new_scale - image_scale) > 1e-6:
                        mx, my = pygame.mouse.get_pos()
                        old_w, old_h = image_rect.size
                        rel_x = (mx - image_rect.x) / old_w if old_w else 0
                        rel_y = (my - image_rect.y) / old_h if old_h else 0
                        # clamp relative position to valid range (handles edge cases)
                        rel_x = max(0.0, min(rel_x, 1.0))
                        rel_y = max(0.0, min(rel_y, 1.0))
                        image_scale = new_scale
                        user_zoomed = True
                        # rescale image surface
                        new_w = max(1, int(orig_w * image_scale))
                        new_h = max(1, int(orig_h * image_scale))
                        image = pygame.transform.smoothscale(original_image, (new_w, new_h))
                        # keep mouse point stable
                        new_x = int(mx - rel_x * new_w)
                        new_y = int(my - rel_y * new_h)
                        # ensure image_rect doesn't go out of reasonable bounds
                        # allow some overhang but not excessive
                        max_x = win_w  # left edge can be at most at right edge of window
                        min_x = SIDEBAR_WIDTH - new_w  # allow scrolling off left edge
                        max_y = win_h  # top edge can be at most at bottom of window
                        min_y = -new_h  # allow scrolling off top edge
                        new_x = max(int(min_x), min(int(max_x), new_x))
                        new_y = max(int(min_y), min(int(max_y), new_y))
                        image_rect = pygame.Rect(new_x, new_y, new_w, new_h)

                pass

        screen.fill(BG_COLOR)

        # (sidebar drawn after image and grid)

        # draw image (may overlap sidebar by design)
        if image:
            screen.blit(image, image_rect)

        # create a label font that scales with image zoom so labels grow/shrink with zoom
            # use a fixed base font and scale rendered surfaces to avoid per-glyph jitter
            try:
                base_label_size = 20
                # prefer a monospace/tabular-number font so digits render uniformly
                monos = ['Consolas', 'Segoe UI Mono', 'Courier New', 'DejaVu Sans Mono']
                fpath = None
                for name in monos:
                    try:
                        m = pygame.font.match_font(name)
                        if m:
                            fpath = m
                            break
                    except Exception:
                        continue
                if fpath:
                    base_label_font = pygame.font.Font(fpath, base_label_size)
                else:
                    base_label_font = pygame.font.SysFont(None, base_label_size)
            except Exception:
                base_label_font = font
            # compute text scale factor applied to base surfaces
            text_scale = image_scale * label_scale

        # draw scale/measurement objects over image
        if scale_object:
            scale_object.draw(screen, image_rect, image_scale, base_label_font, pixels_per_meter=pixels_per_meter, label_scale=text_scale)
        for obj in objects:
            obj.draw(screen, image_rect, image_scale, base_label_font, pixels_per_meter=pixels_per_meter, label_scale=text_scale)

        # draw selection highlight/handles
        if selected_obj:
            try:
                HCOL = (255,220,80)
                if isinstance(selected_obj, ScaleLine) or isinstance(selected_obj, MeasureLine):
                    x1 = image_rect.x + int(selected_obj.p1[0] * image_scale)
                    y1 = image_rect.y + int(selected_obj.p1[1] * image_scale)
                    x2 = image_rect.x + int(selected_obj.p2[0] * image_scale)
                    y2 = image_rect.y + int(selected_obj.p2[1] * image_scale)
                    if obj_dragging:
                        # draw the whole line in highlight color and draw arrows/caps depending on type
                        pygame.draw.line(screen, HCOL, (x1, y1), (x2, y2), max(2, int(selected_obj.width) + 2))
                        if isinstance(selected_obj, MeasureLine):
                            draw_arrow_ends(screen, (x1, y1), (x2, y2), HCOL, size=max(6, int(selected_obj.width*3)), width=max(1, selected_obj.width))
                        else:
                            # scale line: show perpendicular caps
                            draw_perp_cap(screen, (x1, y1), (x2, y2), HCOL, length=12, width=max(1, selected_obj.width))
                    else:
                        # selection not moving: show highlight and endpoint handles (small squares)
                        pygame.draw.line(screen, HCOL, (x1, y1), (x2, y2), max(2, int(selected_obj.width) + 2))
                        pygame.draw.rect(screen, HCOL, (x1-4, y1-4, 8, 8))
                        pygame.draw.rect(screen, HCOL, (x2-4, y2-4, 8, 8))
                elif isinstance(selected_obj, Rectangle):
                    rx = image_rect.x + int(min(selected_obj.p1[0], selected_obj.p2[0]) * image_scale)
                    ry = image_rect.y + int(min(selected_obj.p1[1], selected_obj.p2[1]) * image_scale)
                    rw = int(abs(selected_obj.p2[0] - selected_obj.p1[0]) * image_scale)
                    rh = int(abs(selected_obj.p2[1] - selected_obj.p1[1]) * image_scale)
                    pygame.draw.rect(screen, HCOL, (rx, ry, rw, rh), max(2, selected_obj.width + 1))
                    # corner handles
                    for cx, cy in ((rx, ry), (rx+rw, ry), (rx, ry+rh), (rx+rw, ry+rh)):
                        pygame.draw.rect(screen, HCOL, (cx-4, cy-4, 8, 8))
            except Exception:
                pass

        # draw preview while dragging to add scale/measure/rect
        if 'drawing' in locals() and drawing and mode in ('setting_scale', 'add_measure', 'add_rect'):
            sx1, sy1 = draw_start
            sx2, sy2 = draw_current
            # anti-aliased preview line/rect
            try:
                if mode == 'add_rect':
                    rx = min(sx1, sx2)
                    ry = min(sy1, sy2)
                    rw = abs(sx2 - sx1)
                    rh = abs(sy2 - sy1)
                    pygame.draw.rect(screen, (255, 150, 50), (rx, ry, rw, rh), 2)
                else:
                    pygame.draw.aaline(screen, (255, 150, 50), (sx1, sy1), (sx2, sy2))
            except Exception:
                if mode == 'add_rect':
                    pygame.draw.rect(screen, (255, 150, 50), (min(sx1, sx2), min(sy1, sy2), abs(sx2 - sx1), abs(sy2 - sy1)), 2)
                else:
                    pygame.draw.line(screen, (255, 150, 50), (sx1, sy1), (sx2, sy2), 1)
            # preview caps/arrows instead of end dots
            if mode == 'setting_scale':
                draw_perp_cap(screen, (sx1, sy1), (sx2, sy2), (255, 150, 50), length=8, width=3)
            elif mode == 'add_measure':
                draw_arrow_ends(screen, (sx1, sy1), (sx2, sy2), (255, 150, 50), size=8, width=2)
                # show live measurement during preview
                # compute original-image pixel distance
                ox1 = (sx1 - image_rect.x) / image_scale
                oy1 = (sy1 - image_rect.y) / image_scale
                ox2 = (sx2 - image_rect.x) / image_scale
                oy2 = (sy2 - image_rect.y) / image_scale
                dp = math.hypot(ox2 - ox1, oy2 - oy1)
                if pixels_per_meter:
                    meters = dp / pixels_per_meter
                else:
                    meters = None
                if meters is not None:
                    txt = f"{meters:.2f} m"
                else:
                    txt = f"{int(round(dp))} px"
                try:
                    # render from base font and smoothscale to avoid jitter
                    base_shadow = base_label_font.render(txt, True, (10,10,10))
                    base_img = base_label_font.render(txt, True, (255,220,80))
                    s = max(0.01, float(text_scale))
                    tw = max(1, int(base_img.get_width() * s))
                    th = max(1, int(base_img.get_height() * s))
                    try:
                        shadow = pygame.transform.smoothscale(base_shadow, (tw, th))
                        img = pygame.transform.smoothscale(base_img, (tw, th))
                    except Exception:
                        shadow = pygame.transform.scale(base_shadow, (tw, th))
                        img = pygame.transform.scale(base_img, (tw, th))
                    midx = (sx1 + sx2)//2
                    midy = (sy1 + sy2)//2
                    screen.blit(shadow, (midx - shadow.get_width()//2 + 1, midy - shadow.get_height()//2 + 1))
                    screen.blit(img, (midx - img.get_width()//2, midy - img.get_height()//2))
                except Exception:
                    pass
            elif mode == 'add_rect':
                # show live rectangle dimensions in meters if scale known. Use original-image coords
                ox1 = (sx1 - image_rect.x) / image_scale
                oy1 = (sy1 - image_rect.y) / image_scale
                ox2 = (sx2 - image_rect.x) / image_scale
                oy2 = (sy2 - image_rect.y) / image_scale
                disp_w = abs(sx2 - sx1)
                disp_h = abs(sy2 - sy1)
                rect_orig_w = abs(ox2 - ox1)
                rect_orig_h = abs(oy2 - oy1)
                # prefer meters if scale known, otherwise show pixels
                if pixels_per_meter:
                    wtxt = f"{(rect_orig_w / pixels_per_meter):.2f} m"
                    htxt = f"{(rect_orig_h / pixels_per_meter):.2f} m"
                else:
                    wtxt = f"{int(round(rect_orig_w))} px"
                    htxt = f"{int(round(rect_orig_h))} px"
                try:
                    # scaled rendering for width label
                    base_wshadow = base_label_font.render(wtxt, True, (10,10,10))
                    base_wimg = base_label_font.render(wtxt, True, (255,220,80))
                    s_w = max(0.01, float(text_scale))
                    tw = max(1, int(base_wimg.get_width() * s_w))
                    th = max(1, int(base_wimg.get_height() * s_w))
                    try:
                        wshadow = pygame.transform.smoothscale(base_wshadow, (tw, th))
                        wimg = pygame.transform.smoothscale(base_wimg, (tw, th))
                    except Exception:
                        wshadow = pygame.transform.scale(base_wshadow, (tw, th))
                        wimg = pygame.transform.scale(base_wimg, (tw, th))
                    tx = min(sx1, sx2) + disp_w//2
                    ty = min(sy1, sy2) - max(14, base_label_font.get_linesize())
                    screen.blit(wshadow, (tx - wshadow.get_width()//2 + 1, ty + 1))
                    screen.blit(wimg, (tx - wimg.get_width()//2, ty))

                    # scaled rendering for height label
                    base_hshadow = base_label_font.render(htxt, True, (10,10,10))
                    base_himg = base_label_font.render(htxt, True, (255,220,80))
                    s_h = max(0.01, float(text_scale))
                    tw2 = max(1, int(base_himg.get_width() * s_h))
                    th2 = max(1, int(base_himg.get_height() * s_h))
                    try:
                        hshadow = pygame.transform.smoothscale(base_hshadow, (tw2, th2))
                        himg = pygame.transform.smoothscale(base_himg, (tw2, th2))
                    except Exception:
                        hshadow = pygame.transform.scale(base_hshadow, (tw2, th2))
                        himg = pygame.transform.scale(base_himg, (tw2, th2))
                    lx = min(sx1, sx2) - max(34, base_label_font.get_linesize() + 6)
                    ly = min(sy1, sy2) + disp_h//2
                    screen.blit(hshadow, (lx + 1, ly - hshadow.get_height()//2 + 1))
                    screen.blit(himg, (lx, ly - himg.get_height()//2))
                except Exception:
                    pass

        # draw grid (aligned to image)
        if image and pixels_per_meter and grid_visible:
            # pixels_per_meter is relative to original image pixels; scale to display
            spacing_px = pixels_per_meter * image_scale * grid_spacing_m
            if spacing_px >= 4:  # avoid insane dense grids
                ox, oy = image_rect.topleft
                w, h = image_rect.size
                # align grid to image origin, apply manual offset in pixels
                step = spacing_px
                # compute starting x/y using offset so dragging shifts grid
                try:
                    ox_offset = grid_offset_px[0]
                    oy_offset = grid_offset_px[1]
                except Exception:
                    ox_offset = 0.0
                    oy_offset = 0.0
                start_x = ox + (ox_offset % step) - step
                x = start_x
                while x < ox + w:
                    if int(x) >= SIDEBAR_WIDTH + 2:
                        try:
                            pygame.draw.aaline(screen, GRID_COLOR, (int(x), oy), (int(x), oy + h))
                        except Exception:
                            pygame.draw.line(screen, GRID_COLOR, (int(x), oy), (int(x), oy + h), 1)
                    x += step
                start_y = oy + (oy_offset % step) - step
                y = start_y
                while y < oy + h:
                    try:
                        pygame.draw.aaline(screen, GRID_COLOR, (ox, int(y)), (ox + w, int(y)))
                    except Exception:
                        pygame.draw.line(screen, GRID_COLOR, (ox, int(y)), (ox + w, int(y)), 1)
                    y += step
                # finished grid draw

            # draw scale preview (if in setting mode and one point clicked)
            # (hint will be drawn after the sidebar to ensure visibility)

        # draw sidebar on top so it never gets overlapped
        sidebar_rect = pygame.Rect(0, 0, SIDEBAR_WIDTH, win_h)
        pygame.draw.rect(screen, SIDEBAR_COLOR, sidebar_rect)
        controls = (
            "Controls:\n"
            "O: Open image\n"
            "S: Set scale (drag line)\n"
            "L: Add measurement (drag line)\n"
            "D: Add rectangle (drag)\n"
            "Q: Quicksave current project\n"
            "Hold Shift: snap H/V\n"
            "G: Grid spacing (cm)\n"
            "V: Toggle grid\n"
            "C: Cancel current operation\n"
            "P: Save project | J: Load project\n"
            "K: Open projects folder\n"
            "Delete: Delete selected object\n"
            "Ctrl+Z / Ctrl+Y: Undo / Redo\n"
            "Esc: Quit\n"
        )
        # draw current mode and controls with padding
        mode_name = "Normal"
        if mode == 'setting_scale':
            mode_name = "Adding scale"
        elif mode == 'add_measure':
            mode_name = "Adding line"
        elif mode == 'add_rect':
            mode_name = "Adding rectangle"
        base_y = 10
        draw_text(screen, f"Mode: {mode_name}", (10, base_y), sidebar_font)
        draw_text(screen, controls, (10, base_y + 30 + TEXT_PADDING), sidebar_font)
        # place cancel button below controls to avoid overlap
        controls_lines = controls.count('\n') + 1
        controls_height = controls_lines * sidebar_font.get_linesize()
        cancel_y = base_y + 30 + TEXT_PADDING + controls_height + 8
        if mode in ('setting_scale', 'add_measure', 'add_rect'):
            cancel_rect = pygame.Rect(10, cancel_y, SIDEBAR_WIDTH - 20, 30)
            pygame.draw.rect(screen, (100, 40, 40), cancel_rect)
            draw_text(screen, "Cancel (C)", (cancel_rect.x + 8, cancel_rect.y + 6), sidebar_font, color=(220,220,220))
        else:
            # place hint below the controls block to avoid overlap
            hint_y = cancel_y
            draw_text(screen, "Drag inside image to pan.", (10, hint_y), sidebar_font)

        # draw current scale indicator in sidebar (below controls)
        scale_y = cancel_y + 44
        if pixels_per_meter:
            px_len = pixels_per_meter * image_scale * 1.0
            # cap the drawn length so it doesn't overflow the sidebar
            max_len = max(0, SIDEBAR_WIDTH - 20)
            draw_len = min(int(px_len), max_len)
            sx = 10
            sy = scale_y
            draw_text(screen, f"1.0 m = {px_len:.1f} px", (sx, sy), sidebar_font)
            draw_text(screen, f"Grid spacing: {grid_spacing_m*100:.0f} cm", (sx, sy + 30), sidebar_font)

        # draw line-width slider
        slider_y = scale_y + 70
        slider_x = 10
        slider_w = SIDEBAR_WIDTH - 20
        slider_h = 18
        slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        # track
        pygame.draw.rect(screen, (70,70,70), slider_rect)
        # knob position
        rel = (object_line_width - SLIDER_MIN) / float(SLIDER_MAX - SLIDER_MIN)
        knob_x = slider_x + int(rel * (slider_w - 10))
        knob_rect = pygame.Rect(knob_x, slider_y - 4, 10, slider_h + 8)
        pygame.draw.rect(screen, (200,200,200), knob_rect)
        draw_text(screen, f"Line width: {object_line_width}", (slider_x, slider_y - 22), sidebar_font)
        # label-size slider below line-width
        label_slider_y = slider_y + slider_h + 34
        label_slider_x = slider_x
        label_slider_w = slider_w
        label_slider_h = slider_h
        label_slider_rect = pygame.Rect(label_slider_x, label_slider_y, label_slider_w, label_slider_h)
        pygame.draw.rect(screen, (70,70,70), label_slider_rect)
        # knob for label scale
        lrel = (label_scale - LABEL_SCALE_MIN) / float(LABEL_SCALE_MAX - LABEL_SCALE_MIN)
        lknob_x = label_slider_x + int(lrel * (label_slider_w - 10))
        lknob_rect = pygame.Rect(lknob_x, label_slider_y - 4, 10, label_slider_h + 8)
        pygame.draw.rect(screen, (200,200,200), lknob_rect)
        draw_text(screen, f"Label scale: {label_scale:.2f}x", (label_slider_x, label_slider_y - 22), sidebar_font)
        # hint to open projects folder
        draw_text(screen, "K: Open projects folder", (slider_x, label_slider_y + label_slider_h + 8), sidebar_font)

        # draw drag hint after sidebar so it is not overlapped by the image
        if mode == 'setting_scale' and drawing:
            draw_text(screen, "Drag and release to set scale; hold Shift to snap", (SIDEBAR_WIDTH + 10, win_h - 50), font)
        # transient quicksave popup (top center of image area)
        try:
            now = pygame.time.get_ticks()
        except Exception:
            now = 0
        if quicksave_popup_until and now and now < quicksave_popup_until:
            try:
                popup_txt = quicksave_msg or 'Quicksaved'
                popup_img = sidebar_font.render(popup_txt, True, (255,255,255))
                pad = 8
                pw = popup_img.get_width() + pad*2
                ph = popup_img.get_height() + pad*2
                px = SIDEBAR_WIDTH + max(0, (win_w - SIDEBAR_WIDTH - pw)//2)
                py = 8
                pygame.draw.rect(screen, (30,30,30), (px, py, pw, ph))
                screen.blit(popup_img, (px + pad, py + pad))
            except Exception:
                pass
        # flip display

        pygame.display.flip()
        clock.tick(60)
        if frame_count < 3:
            pass
        frame_count += 1

    pygame.quit()
    # main exiting

if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        # pause so user/runner can see the traceback
        try:
            input("Error occurred. Press Enter to exit...")
        except Exception:
            pass
