#!/usr/bin/env python3
"""
Intersect Engine GUI Editor v1.0
A visual editor for Intersect Engine GUI JSON files.
Supports drag & drop, real game coordinates (800x600 / 1024x768),
file explorer for GUI folders, and property editing.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import json
import os
import copy
from pathlib import Path
from PIL import Image, ImageTk

# ─── Constants ──────────────────────────────────────────────────────
GAME_RESOLUTIONS = {
    "800x600": (800, 600),
    "1024x768": (1024, 768),
    "1280x720": (1280, 720),
    "1920x1080": (1920, 1080),
}
DEFAULT_RES = "1024x768"
GRID_SIZE = 8
HANDLE_SIZE = 8
BG_COLOR = "#1e1e2e"
CANVAS_BG = "#2d2d44"
PANEL_BG = "#252536"
TEXT_COLOR = "#cdd6f4"
ACCENT = "#89b4fa"
ACCENT2 = "#f38ba8"
BORDER_COLOR = "#45475a"
HOVER_COLOR = "#313244"
SELECT_COLOR = "#585b70"

# ─── Helper: Deep get/set in nested dict ────────────────────────────
def deep_get(d, keys, default=None):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d

def deep_set(d, keys, value):
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


class GUIElement:
    """Represents a single GUI element from JSON."""
    def __init__(self, name, data, parent=None):
        self.name = name
        self.data = data
        self.parent = parent
        self.children = []
        self.visible = True
        self.locked = False

        # Parse bounds
        bounds = data.get("Bounds", "")
        self.x, self.y, self.w, self.h = self._parse_bounds(bounds)

        # Texture
        self.texture = data.get("Texture", "")
        self.texture_image = None  # PIL image
        self.tk_image = None  # PhotoImage

    def _parse_bounds(self, bounds_str):
        if not bounds_str or not isinstance(bounds_str, str):
            return 0, 0, 100, 50
        parts = bounds_str.replace("{", "").replace("}", "").split(",")
        try:
            vals = []
            for p in parts:
                p = p.strip()
                if "=" in p:
                    p = p.split("=")[1]
                vals.append(int(p.strip()))
            if len(vals) >= 4:
                return vals[0], vals[1], vals[2], vals[3]
        except (ValueError, IndexError):
            pass
        return 0, 0, 100, 50

    def update_bounds(self):
        self.data["Bounds"] = f"{{X={self.x},Y={self.y},Width={self.w},Height={self.h}}}"

    def get_absolute_pos(self):
        """Get absolute position by accumulating parent offsets."""
        ax, ay = self.x, self.y
        p = self.parent
        while p is not None:
            ax += p.x
            ay += p.y
            p = p.parent
        return ax, ay

    def hit_test(self, mx, my):
        ax, ay = self.get_absolute_pos()
        return ax <= mx <= ax + self.w and ay <= my <= ay + self.h


class FileExplorer(ttk.Frame):
    """File explorer panel to browse a GUI folder."""
    def __init__(self, master, on_file_select, **kwargs):
        super().__init__(master, **kwargs)
        self.on_file_select = on_file_select
        self.current_folder = None
        self.gui_folder = None

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=4, pady=(4, 0))
        ttk.Label(header, text="📂 Explorateur", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(header, text="Ouvrir dossier", command=self.open_folder, width=14).pack(side="right")

        # Filter
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", padx=4, pady=2)
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *a: self.refresh_tree())
        ttk.Entry(filter_frame, textvariable=self.filter_var).pack(fill="x")

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        self.file_paths = {}

    def open_folder(self, folder_path=None):
        if folder_path is None:
            folder_path = filedialog.askdirectory(title="Sélectionner le dossier GUI d'Intersect")
        if not folder_path:
            return
        self.gui_folder = folder_path
        self.current_folder = folder_path
        self.refresh_tree()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.file_paths.clear()
        if not self.current_folder:
            return

        filter_text = self.filter_var.get().lower()

        def add_entries(parent_id, path):
            try:
                entries = sorted(os.listdir(path))
            except PermissionError:
                return
            # Folders first, then files
            dirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]
            files = [e for e in entries if os.path.isfile(os.path.join(path, e))]

            for d in dirs:
                full = os.path.join(path, d)
                node = self.tree.insert(parent_id, "end", text=f"📁 {d}", open=False)
                self.file_paths[node] = full
                add_entries(node, full)

            for f in files:
                if filter_text and filter_text not in f.lower():
                    continue
                full = os.path.join(path, f)
                icon = "📄"
                if f.lower().endswith(".json"):
                    icon = "🔧"
                elif f.lower().endswith((".png", ".jpg", ".bmp")):
                    icon = "🖼️"
                node = self.tree.insert(parent_id, "end", text=f"{icon} {f}")
                self.file_paths[node] = full

        add_entries("", self.current_folder)

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        path = self.file_paths.get(sel[0], "")
        if path.lower().endswith(".json"):
            self.on_file_select(path)


class ElementTree(ttk.Frame):
    """Tree view showing the element hierarchy."""
    def __init__(self, master, on_select, on_visibility_toggle, **kwargs):
        super().__init__(master, **kwargs)
        self.on_select = on_select
        self.on_visibility_toggle = on_visibility_toggle

        header = ttk.Frame(self)
        header.pack(fill="x", padx=4, pady=(4, 0))
        ttk.Label(header, text="🌳 Éléments", font=("Segoe UI", 10, "bold")).pack(side="left")

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.element_map = {}

    def populate(self, elements, parent=""):
        self.tree.delete(*self.tree.get_children())
        self.element_map.clear()
        self._add_elements(elements, parent)

    def _add_elements(self, elements, parent):
        for elem in elements:
            vis = "👁" if elem.visible else "🚫"
            text = f"{vis} {elem.name} ({elem.w}x{elem.h})"
            node = self.tree.insert(parent, "end", text=text, open=True)
            self.element_map[node] = elem
            if elem.children:
                self._add_elements(elem.children, node)

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            elem = self.element_map.get(sel[0])
            if elem:
                self.on_select(elem)

    def select_element(self, elem):
        for node, el in self.element_map.items():
            if el is elem:
                self.tree.selection_set(node)
                self.tree.see(node)
                break


class PropertyPanel(ttk.Frame):
    """Property editor for selected elements."""
    def __init__(self, master, on_property_change, **kwargs):
        super().__init__(master, **kwargs)
        self.on_property_change = on_property_change
        self.current_element = None

        header = ttk.Frame(self)
        header.pack(fill="x", padx=4, pady=(4, 0))
        ttk.Label(header, text="⚙️ Propriétés", font=("Segoe UI", 10, "bold")).pack(side="left")

        # Scrollable content
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scrollbar.pack(side="right", fill="y")

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

        self.widgets = []

    def show_element(self, elem):
        self.current_element = elem
        # Clear
        for w in self.widgets:
            w.destroy()
        self.widgets.clear()

        if elem is None:
            return

        # Name (read-only)
        self._add_label("Nom")
        self._add_readonly("name_val", elem.name)

        # Position
        self._add_label("Position & Taille")
        pos_frame = ttk.Frame(self.scroll_frame)
        pos_frame.pack(fill="x", pady=2)
        self.widgets.append(pos_frame)

        for label, attr in [("X:", "x"), ("Y:", "y"), ("W:", "w"), ("H:", "h")]:
            ttk.Label(pos_frame, text=label, width=3).pack(side="left")
            var = tk.StringVar(value=str(getattr(elem, attr)))
            entry = ttk.Entry(pos_frame, textvariable=var, width=6)
            entry.pack(side="left", padx=(0, 4))
            var.trace_add("write", lambda *a, at=attr, v=var: self._update_pos(at, v))

        # Texture
        self._add_label("Texture")
        tex_var = tk.StringVar(value=elem.texture or "")
        tex_entry = ttk.Entry(self.scroll_frame, textvariable=tex_var)
        tex_entry.pack(fill="x", pady=2)
        self.widgets.append(tex_entry)
        tex_var.trace_add("write", lambda *a: self._update_texture(tex_var))

        # Common properties
        self._add_label("Propriétés")
        common_props = [
            "Hidden", "DrawBackground", "DrawBorder",
            "AlignmentEdgeDistances", "AlignmentTransform",
            "Padding", "Margin", "TextColor", "Color",
        ]
        for prop in common_props:
            if prop in elem.data:
                self._add_property_field(prop, elem.data[prop])

        # All other properties
        self._add_label("Autres propriétés")
        skip = {"Bounds", "Texture", "Name", "Children"} | set(common_props)
        for key, val in elem.data.items():
            if key in skip:
                continue
            if isinstance(val, (str, int, float, bool)):
                self._add_property_field(key, val)

    def _add_label(self, text):
        lbl = ttk.Label(self.scroll_frame, text=text, font=("Segoe UI", 9, "bold"))
        lbl.pack(fill="x", pady=(8, 2))
        self.widgets.append(lbl)

    def _add_readonly(self, name, value):
        lbl = ttk.Label(self.scroll_frame, text=str(value))
        lbl.pack(fill="x", pady=2)
        self.widgets.append(lbl)

    def _add_property_field(self, key, value):
        frame = ttk.Frame(self.scroll_frame)
        frame.pack(fill="x", pady=1)
        self.widgets.append(frame)

        ttk.Label(frame, text=key, width=20, anchor="w").pack(side="left")

        if isinstance(value, bool):
            var = tk.BooleanVar(value=value)
            cb = ttk.Checkbutton(frame, variable=var,
                                 command=lambda: self._update_property(key, var.get()))
            cb.pack(side="left")
        elif isinstance(value, str) and value.startswith("{") and "Color" in key:
            # Color field
            btn = ttk.Button(frame, text=value[:20], width=16,
                             command=lambda k=key, v=value: self._pick_color(k, v))
            btn.pack(side="left")
        else:
            var = tk.StringVar(value=str(value))
            entry = ttk.Entry(frame, textvariable=var, width=20)
            entry.pack(side="left", fill="x", expand=True)
            entry.bind("<Return>", lambda e, k=key, v=var: self._update_property(k, v.get()))
            entry.bind("<FocusOut>", lambda e, k=key, v=var: self._update_property(k, v.get()))

    def _update_pos(self, attr, var):
        if self.current_element is None:
            return
        try:
            val = int(var.get())
            setattr(self.current_element, attr, val)
            self.current_element.update_bounds()
            self.on_property_change(self.current_element)
        except ValueError:
            pass

    def _update_texture(self, var):
        if self.current_element is None:
            return
        self.current_element.texture = var.get()
        self.current_element.data["Texture"] = var.get()
        self.on_property_change(self.current_element)

    def _update_property(self, key, value):
        if self.current_element is None:
            return
        # Try to convert to int/float/bool
        if isinstance(value, str):
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            else:
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
        self.current_element.data[key] = value
        self.on_property_change(self.current_element)

    def _pick_color(self, key, current):
        color = colorchooser.askcolor(title=f"Choisir {key}")
        if color[1]:
            r, g, b = [int(c) for c in color[0]]
            color_str = f"{{A=255, R={r}, G={g}, B={b}}}"
            self.current_element.data[key] = color_str
            self.on_property_change(self.current_element)
            self.show_element(self.current_element)


class GameCanvas(tk.Canvas):
    """The main canvas showing the game preview with elements."""
    def __init__(self, master, on_select, on_move, **kwargs):
        super().__init__(master, bg=CANVAS_BG, highlightthickness=0, **kwargs)
        self.on_select_callback = on_select
        self.on_move_callback = on_move
        self.elements = []
        self.selected = None
        self.game_w, self.game_h = GAME_RESOLUTIONS[DEFAULT_RES]
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_start = None
        self.drag_mode = None  # "move" or "resize_xx"
        self.show_grid = True
        self.snap_to_grid = True
        self.texture_folder = None
        self.texture_cache = {}

        # Bindings
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<MouseWheel>", self._on_scroll)
        self.bind("<ButtonPress-2>", self._on_pan_start)
        self.bind("<B2-Motion>", self._on_pan)
        self.bind("<ButtonPress-3>", self._on_pan_start)
        self.bind("<B3-Motion>", self._on_pan)
        self.bind("<Configure>", lambda e: self.redraw())

    def set_resolution(self, res_name):
        if res_name in GAME_RESOLUTIONS:
            self.game_w, self.game_h = GAME_RESOLUTIONS[res_name]
            self.center_view()
            self.redraw()

    def center_view(self):
        cw = self.winfo_width() or 800
        ch = self.winfo_height() or 600
        self.offset_x = (cw - self.game_w * self.zoom) / 2
        self.offset_y = (ch - self.game_h * self.zoom) / 2

    def set_elements(self, elements):
        self.elements = elements
        self.selected = None
        self.center_view()
        self.load_textures(elements)
        self.redraw()

    def load_textures(self, elements):
        """Try to load texture images for elements."""
        if not self.texture_folder:
            return
        for elem in elements:
            if elem.texture:
                self._load_element_texture(elem)
            if elem.children:
                self.load_textures(elem.children)

    def _load_element_texture(self, elem):
        if not self.texture_folder or not elem.texture:
            return
        tex_name = elem.texture
        if tex_name in self.texture_cache:
            elem.texture_image = self.texture_cache[tex_name]
            return
        # Search for texture in folder and subfolders
        for root, dirs, files in os.walk(self.texture_folder):
            for f in files:
                if f.lower() == tex_name.lower():
                    try:
                        img = Image.open(os.path.join(root, f))
                        self.texture_cache[tex_name] = img
                        elem.texture_image = img
                        return
                    except Exception:
                        pass

    def game_to_screen(self, gx, gy):
        return gx * self.zoom + self.offset_x, gy * self.zoom + self.offset_y

    def screen_to_game(self, sx, sy):
        return (sx - self.offset_x) / self.zoom, (sy - self.offset_y) / self.zoom

    def redraw(self):
        self.delete("all")

        # Game area background
        sx, sy = self.game_to_screen(0, 0)
        ex, ey = self.game_to_screen(self.game_w, self.game_h)
        self.create_rectangle(sx, sy, ex, ey, fill="#1a1a2e", outline="#444466", width=2)

        # Grid
        if self.show_grid and self.zoom >= 0.5:
            step = GRID_SIZE
            if self.zoom < 0.8:
                step = GRID_SIZE * 4
            for gx in range(0, self.game_w + 1, step):
                x1, y1 = self.game_to_screen(gx, 0)
                x2, y2 = self.game_to_screen(gx, self.game_h)
                self.create_line(x1, y1, x2, y2, fill="#2a2a3e", width=1)
            for gy in range(0, self.game_h + 1, step):
                x1, y1 = self.game_to_screen(0, gy)
                x2, y2 = self.game_to_screen(self.game_w, gy)
                self.create_line(x1, y1, x2, y2, fill="#2a2a3e", width=1)

        # Draw elements
        self._draw_elements(self.elements)

        # Selection handles
        if self.selected:
            self._draw_selection(self.selected)

        # Resolution label
        self.create_text(sx + 5, sy + 5, text=f"{self.game_w}x{self.game_h}",
                         fill="#666688", anchor="nw", font=("Consolas", 9))

    def _draw_elements(self, elements):
        for elem in elements:
            if not elem.visible:
                continue
            ax, ay = elem.get_absolute_pos()
            x1, y1 = self.game_to_screen(ax, ay)
            x2, y2 = self.game_to_screen(ax + elem.w, ay + elem.h)

            # Draw texture if available
            if elem.texture_image:
                try:
                    tw = max(1, int(elem.w * self.zoom))
                    th = max(1, int(elem.h * self.zoom))
                    resized = elem.texture_image.resize((tw, th), Image.LANCZOS)
                    tk_img = ImageTk.PhotoImage(resized)
                    elem.tk_image = tk_img  # Keep reference
                    self.create_image(x1, y1, image=tk_img, anchor="nw")
                except Exception:
                    self._draw_rect_element(elem, x1, y1, x2, y2)
            else:
                self._draw_rect_element(elem, x1, y1, x2, y2)

            # Draw children
            if elem.children:
                self._draw_elements(elem.children)

    def _draw_rect_element(self, elem, x1, y1, x2, y2):
        is_sel = elem is self.selected
        fill_color = "#3d3d5c" if not is_sel else "#4a4a70"
        outline_color = ACCENT if is_sel else "#555577"
        width = 2 if is_sel else 1

        self.create_rectangle(x1, y1, x2, y2, fill=fill_color,
                              outline=outline_color, width=width)

        # Element name
        if (x2 - x1) > 30 and (y2 - y1) > 14:
            font_size = max(7, min(10, int(10 * self.zoom)))
            name = elem.name
            if len(name) > 20:
                name = name[:18] + "…"
            self.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                             text=name, fill=TEXT_COLOR,
                             font=("Segoe UI", font_size), anchor="center")

    def _draw_selection(self, elem):
        ax, ay = elem.get_absolute_pos()
        x1, y1 = self.game_to_screen(ax, ay)
        x2, y2 = self.game_to_screen(ax + elem.w, ay + elem.h)
        hs = HANDLE_SIZE

        # Dashed outline
        self.create_rectangle(x1 - 1, y1 - 1, x2 + 1, y2 + 1,
                              outline=ACCENT2, dash=(4, 4), width=1)

        # Resize handles
        handles = [
            ("nw", x1, y1), ("n", (x1 + x2) / 2, y1), ("ne", x2, y1),
            ("w", x1, (y1 + y2) / 2), ("e", x2, (y1 + y2) / 2),
            ("sw", x1, y2), ("s", (x1 + x2) / 2, y2), ("se", x2, y2),
        ]
        for name, hx, hy in handles:
            self.create_rectangle(hx - hs / 2, hy - hs / 2, hx + hs / 2, hy + hs / 2,
                                  fill=ACCENT, outline="white", width=1)

        # Position info
        self.create_text(x1, y1 - 12,
                         text=f"({elem.x}, {elem.y}) {elem.w}×{elem.h}",
                         fill=ACCENT, anchor="sw", font=("Consolas", 8))

    def _on_press(self, event):
        mx, my = event.x, event.y

        # Check resize handles first
        if self.selected:
            handle = self._hit_test_handles(mx, my)
            if handle:
                self.drag_mode = f"resize_{handle}"
                self.drag_start = (mx, my, self.selected.x, self.selected.y,
                                   self.selected.w, self.selected.h)
                return

        # Hit test elements (reverse order = top first)
        gx, gy = self.screen_to_game(mx, my)
        hit = self._find_element_at(gx, gy, self.elements)
        if hit:
            self.selected = hit
            self.drag_mode = "move"
            self.drag_start = (mx, my, hit.x, hit.y, hit.w, hit.h)
            self.on_select_callback(hit)
        else:
            self.selected = None
            self.on_select_callback(None)

        self.redraw()

    def _find_element_at(self, gx, gy, elements):
        """Find topmost element at game coordinates (depth-first, reverse)."""
        for elem in reversed(elements):
            if not elem.visible:
                continue
            # Check children first (they're on top)
            if elem.children:
                child_hit = self._find_element_at(gx, gy, elem.children)
                if child_hit:
                    return child_hit
            if elem.hit_test(gx, gy):
                return elem
        return None

    def _hit_test_handles(self, mx, my):
        if not self.selected:
            return None
        ax, ay = self.selected.get_absolute_pos()
        x1, y1 = self.game_to_screen(ax, ay)
        x2, y2 = self.game_to_screen(ax + self.selected.w, ay + self.selected.h)
        hs = HANDLE_SIZE + 2

        handles = {
            "nw": (x1, y1), "n": ((x1 + x2) / 2, y1), "ne": (x2, y1),
            "w": (x1, (y1 + y2) / 2), "e": (x2, (y1 + y2) / 2),
            "sw": (x1, y2), "s": ((x1 + x2) / 2, y2), "se": (x2, y2),
        }
        for name, (hx, hy) in handles.items():
            if abs(mx - hx) <= hs and abs(my - hy) <= hs:
                return name
        return None

    def _on_drag(self, event):
        if not self.drag_start or not self.selected:
            return
        mx, my = event.x, event.y
        sx, sy, ox, oy, ow, oh = self.drag_start

        dx = (mx - sx) / self.zoom
        dy = (my - sy) / self.zoom

        if self.drag_mode == "move":
            new_x = ox + dx
            new_y = oy + dy
            if self.snap_to_grid:
                new_x = round(new_x / GRID_SIZE) * GRID_SIZE
                new_y = round(new_y / GRID_SIZE) * GRID_SIZE
            self.selected.x = int(new_x)
            self.selected.y = int(new_y)

        elif self.drag_mode and self.drag_mode.startswith("resize_"):
            handle = self.drag_mode.split("_")[1]
            new_x, new_y, new_w, new_h = ox, oy, ow, oh

            if "e" in handle:
                new_w = max(8, ow + dx)
            if "w" in handle:
                new_w = max(8, ow - dx)
                new_x = ox + dx if new_w > 8 else ox
            if "s" in handle:
                new_h = max(8, oh + dy)
            if "n" in handle:
                new_h = max(8, oh - dy)
                new_y = oy + dy if new_h > 8 else oy

            if self.snap_to_grid:
                new_x = round(new_x / GRID_SIZE) * GRID_SIZE
                new_y = round(new_y / GRID_SIZE) * GRID_SIZE
                new_w = round(new_w / GRID_SIZE) * GRID_SIZE
                new_h = round(new_h / GRID_SIZE) * GRID_SIZE

            self.selected.x = int(new_x)
            self.selected.y = int(new_y)
            self.selected.w = int(max(8, new_w))
            self.selected.h = int(max(8, new_h))

        self.selected.update_bounds()
        self.on_move_callback(self.selected)
        self.redraw()

    def _on_release(self, event):
        self.drag_start = None
        self.drag_mode = None

    def _on_scroll(self, event):
        old_zoom = self.zoom
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom = max(0.1, min(5.0, self.zoom * factor))

        # Zoom toward cursor
        mx, my = event.x, event.y
        self.offset_x = mx - (mx - self.offset_x) * (self.zoom / old_zoom)
        self.offset_y = my - (my - self.offset_y) * (self.zoom / old_zoom)

        self.redraw()

    def _on_pan_start(self, event):
        self._pan_start = (event.x, event.y, self.offset_x, self.offset_y)

    def _on_pan(self, event):
        if hasattr(self, "_pan_start"):
            sx, sy, ox, oy = self._pan_start
            self.offset_x = ox + (event.x - sx)
            self.offset_y = oy + (event.y - sy)
            self.redraw()


class IntersectGUIEditor:
    """Main application class."""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Intersect GUI Editor v1.0")
        self.root.geometry("1400x900")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(1000, 600)

        # Apply dark theme
        self.setup_theme()

        self.elements = []
        self.current_file = None
        self.original_data = None
        self.undo_stack = []
        self.redo_stack = []

        self.build_ui()

        # Center on screen
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def setup_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=PANEL_BG, foreground=TEXT_COLOR,
                         fieldbackground="#1e1e2e", bordercolor=BORDER_COLOR,
                         troughcolor="#1e1e2e", selectbackground=ACCENT,
                         selectforeground="white", font=("Segoe UI", 9))

        style.configure("TButton", padding=(8, 4), background="#3d3d5c",
                         foreground=TEXT_COLOR)
        style.map("TButton",
                   background=[("active", ACCENT), ("pressed", "#7aa2f7")])

        style.configure("TEntry", fieldbackground="#1e1e2e", padding=4)
        style.configure("TLabel", background=PANEL_BG, foreground=TEXT_COLOR)
        style.configure("TFrame", background=PANEL_BG)
        style.configure("TCheckbutton", background=PANEL_BG, foreground=TEXT_COLOR)
        style.configure("TCombobox", fieldbackground="#1e1e2e", padding=4)

        style.configure("Treeview", background="#1e1e2e", foreground=TEXT_COLOR,
                         fieldbackground="#1e1e2e", borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL_BG, foreground=TEXT_COLOR)
        style.map("Treeview",
                   background=[("selected", SELECT_COLOR)],
                   foreground=[("selected", "white")])

        style.configure("TSeparator", background=BORDER_COLOR)

        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                         padding=(12, 6))
        style.map("Accent.TButton",
                   background=[("active", "#7aa2f7"), ("pressed", "#6690e0")])

    def build_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root, bg=PANEL_BG, fg=TEXT_COLOR,
                          activebackground=ACCENT, activeforeground="white")

        file_menu = tk.Menu(menubar, tearoff=0, bg=PANEL_BG, fg=TEXT_COLOR,
                            activebackground=ACCENT, activeforeground="white")
        file_menu.add_command(label="📂 Ouvrir dossier GUI...", command=self.open_folder,
                              accelerator="Ctrl+O")
        file_menu.add_command(label="📄 Ouvrir fichier JSON...", command=self.open_file,
                              accelerator="Ctrl+F")
        file_menu.add_separator()
        file_menu.add_command(label="💾 Sauvegarder", command=self.save_file,
                              accelerator="Ctrl+S")
        file_menu.add_command(label="💾 Sauvegarder sous...", command=self.save_file_as,
                              accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="❌ Quitter", command=self.root.quit)
        menubar.add_cascade(label="Fichier", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0, bg=PANEL_BG, fg=TEXT_COLOR,
                            activebackground=ACCENT, activeforeground="white")
        edit_menu.add_command(label="↩ Annuler", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="↪ Rétablir", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="📋 Dupliquer", command=self.duplicate_element,
                              accelerator="Ctrl+D")
        edit_menu.add_command(label="🗑 Supprimer", command=self.delete_element,
                              accelerator="Delete")
        menubar.add_cascade(label="Edition", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0, bg=PANEL_BG, fg=TEXT_COLOR,
                            activebackground=ACCENT, activeforeground="white")
        self.grid_var = tk.BooleanVar(value=True)
        self.snap_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Grille", variable=self.grid_var,
                                  command=self.toggle_grid)
        view_menu.add_checkbutton(label="Snap to grid", variable=self.snap_var,
                                  command=self.toggle_snap)
        view_menu.add_separator()
        view_menu.add_command(label="🔍 Centrer la vue", command=self.center_view)
        menubar.add_cascade(label="Affichage", menu=view_menu)

        self.root.config(menu=menubar)

        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=4, pady=4)

        ttk.Button(toolbar, text="📂 Dossier", command=self.open_folder).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📄 Fichier", command=self.open_file).pack(side="left", padx=2)
        ttk.Button(toolbar, text="💾 Sauver", command=self.save_file).pack(side="left", padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        ttk.Label(toolbar, text="Résolution:").pack(side="left", padx=(4, 2))
        self.res_var = tk.StringVar(value=DEFAULT_RES)
        res_combo = ttk.Combobox(toolbar, textvariable=self.res_var,
                                  values=list(GAME_RESOLUTIONS.keys()),
                                  state="readonly", width=10)
        res_combo.pack(side="left", padx=2)
        res_combo.bind("<<ComboboxSelected>>", lambda e: self.canvas.set_resolution(self.res_var.get()))

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        ttk.Button(toolbar, text="➕ Ajouter", command=self.add_element).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📋 Dupliquer", command=self.duplicate_element).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🗑 Supprimer", command=self.delete_element).pack(side="left", padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        ttk.Button(toolbar, text="🔍 Centrer", command=self.center_view).pack(side="left", padx=2)

        # Status bar info
        self.status_var = tk.StringVar(value="Prêt — Ouvrez un dossier GUI pour commencer")
        ttk.Label(toolbar, textvariable=self.status_var).pack(side="right", padx=8)

        # Main layout: PanedWindow
        main_pane = ttk.PanedWindow(self.root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Left panel: File Explorer + Element Tree
        left_panel = ttk.PanedWindow(main_pane, orient="vertical")
        main_pane.add(left_panel, weight=0)

        self.file_explorer = FileExplorer(left_panel, on_file_select=self.load_file)
        left_panel.add(self.file_explorer, weight=1)

        self.element_tree = ElementTree(left_panel, on_select=self.on_tree_select,
                                         on_visibility_toggle=self.on_visibility_toggle)
        left_panel.add(self.element_tree, weight=1)

        # Center: Canvas
        canvas_frame = ttk.Frame(main_pane)
        main_pane.add(canvas_frame, weight=3)

        self.canvas = GameCanvas(canvas_frame, on_select=self.on_canvas_select,
                                  on_move=self.on_element_moved)
        self.canvas.pack(fill="both", expand=True)

        # Right panel: Property editor
        self.property_panel = PropertyPanel(main_pane, on_property_change=self.on_property_change)
        main_pane.add(self.property_panel, weight=0)

        # Keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self.open_folder())
        self.root.bind("<Control-f>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-S>", lambda e: self.save_file_as())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-d>", lambda e: self.duplicate_element())
        self.root.bind("<Delete>", lambda e: self.delete_element())

    # ─── File Operations ────────────────────────────────────────────

    def open_folder(self):
        self.file_explorer.open_folder()
        if self.file_explorer.gui_folder:
            self.canvas.texture_folder = self.file_explorer.gui_folder
            # Also look for texture folder nearby
            parent = os.path.dirname(self.file_explorer.gui_folder)
            for folder_name in ["textures", "Textures", "images", "Images", "resources"]:
                tex_path = os.path.join(parent, folder_name)
                if os.path.isdir(tex_path):
                    self.canvas.texture_folder = tex_path
                    break
            self.status_var.set(f"Dossier: {self.file_explorer.gui_folder}")

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Ouvrir un fichier GUI JSON",
            filetypes=[("JSON", "*.json"), ("Tous", "*.*")]
        )
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.current_file = path
            self.original_data = copy.deepcopy(data)
            self.elements = self.parse_json(data)
            self.element_tree.populate(self.elements)
            self.canvas.set_elements(self.elements)
            self.undo_stack.clear()
            self.redo_stack.clear()

            filename = os.path.basename(path)
            self.status_var.set(f"📄 {filename} — {len(self.elements)} éléments racine")
            self.root.title(f"Intersect GUI Editor — {filename}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger le fichier:\n{e}")

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
            return
        self._save_to(self.current_file)

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="Sauvegarder le fichier GUI",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Tous", "*.*")]
        )
        if path:
            self.current_file = path
            self._save_to(path)

    def _save_to(self, path):
        try:
            data = self.elements_to_json(self.elements)
            # If original data was a dict with a root key, preserve structure
            if self.original_data and isinstance(self.original_data, dict):
                output = copy.deepcopy(self.original_data)
                # Find where children are and update
                self._update_json_data(output, self.elements)
            else:
                output = data

            with open(path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            self.status_var.set(f"💾 Sauvegardé: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de sauvegarder:\n{e}")

    def _update_json_data(self, data, elements):
        """Recursively update the original JSON data with modified element positions."""
        if isinstance(data, dict):
            # Check if this dict looks like a GUI element
            if "Bounds" in data:
                # Find matching element
                name = data.get("Name", "")
                for elem in self._flatten_elements(elements):
                    if elem.name == name:
                        data["Bounds"] = elem.data["Bounds"]
                        if "Texture" in data:
                            data["Texture"] = elem.data.get("Texture", "")
                        # Copy other modified properties
                        for k, v in elem.data.items():
                            if k not in ("Children", "Bounds", "Texture"):
                                data[k] = v
                        break
            for key, val in data.items():
                if isinstance(val, dict):
                    self._update_json_data(val, elements)
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            self._update_json_data(item, elements)

    def _flatten_elements(self, elements):
        result = []
        for e in elements:
            result.append(e)
            if e.children:
                result.extend(self._flatten_elements(e.children))
        return result

    # ─── JSON Parsing ───────────────────────────────────────────────

    def parse_json(self, data, parent=None):
        """Parse Intersect Engine GUI JSON into GUIElement tree."""
        elements = []

        if isinstance(data, dict):
            # Try to find GUI elements in the dict
            for key, val in data.items():
                if isinstance(val, dict) and ("Bounds" in val or "Children" in val):
                    elem = GUIElement(key, val, parent)
                    # Parse children
                    children_data = val.get("Children", {})
                    if isinstance(children_data, dict):
                        elem.children = self.parse_json(children_data, elem)
                    elif isinstance(children_data, list):
                        for child_data in children_data:
                            if isinstance(child_data, dict):
                                child_name = child_data.get("Name", f"child_{len(elem.children)}")
                                child = GUIElement(child_name, child_data, elem)
                                child.children = self.parse_json(child_data.get("Children", {}), child)
                                elem.children.append(child)
                    elements.append(elem)
                elif isinstance(val, dict):
                    # Recurse into nested dicts
                    sub = self.parse_json(val, parent)
                    elements.extend(sub)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    name = item.get("Name", f"element_{len(elements)}")
                    elem = GUIElement(name, item, parent)
                    children_data = item.get("Children", {})
                    if isinstance(children_data, dict):
                        elem.children = self.parse_json(children_data, elem)
                    elements.append(elem)

        return elements

    def elements_to_json(self, elements):
        """Convert elements back to JSON dict."""
        result = {}
        for elem in elements:
            elem.update_bounds()
            d = copy.deepcopy(elem.data)
            if elem.children:
                d["Children"] = self.elements_to_json(elem.children)
            result[elem.name] = d
        return result

    # ─── Element Operations ─────────────────────────────────────────

    def add_element(self):
        name = simpledialog.askstring("Ajouter un élément", "Nom de l'élément:")
        if not name:
            return
        self.push_undo()
        data = {
            "Bounds": "{X=100,Y=100,Width=100,Height=50}",
            "Texture": "",
            "Hidden": False,
            "Children": {},
        }
        elem = GUIElement(name, data)
        self.elements.append(elem)
        self.element_tree.populate(self.elements)
        self.canvas.set_elements(self.elements)

    def duplicate_element(self):
        if not self.canvas.selected:
            return
        self.push_undo()
        src = self.canvas.selected
        new_data = copy.deepcopy(src.data)
        new_name = f"{src.name}_copy"
        new_elem = GUIElement(new_name, new_data, src.parent)
        new_elem.x = src.x + 16
        new_elem.y = src.y + 16
        new_elem.update_bounds()

        if src.parent:
            src.parent.children.append(new_elem)
        else:
            self.elements.append(new_elem)

        self.element_tree.populate(self.elements)
        self.canvas.redraw()

    def delete_element(self):
        if not self.canvas.selected:
            return
        self.push_undo()
        elem = self.canvas.selected
        if elem.parent:
            elem.parent.children.remove(elem)
        else:
            self.elements.remove(elem)

        self.canvas.selected = None
        self.element_tree.populate(self.elements)
        self.canvas.redraw()
        self.property_panel.show_element(None)

    # ─── Selection & Events ─────────────────────────────────────────

    def on_canvas_select(self, elem):
        self.property_panel.show_element(elem)
        if elem:
            self.element_tree.select_element(elem)
        self.push_undo()

    def on_tree_select(self, elem):
        self.canvas.selected = elem
        self.canvas.redraw()
        self.property_panel.show_element(elem)

    def on_element_moved(self, elem):
        self.property_panel.show_element(elem)
        self.element_tree.populate(self.elements)
        if elem:
            self.element_tree.select_element(elem)

    def on_property_change(self, elem):
        self.canvas.redraw()
        self.element_tree.populate(self.elements)
        if elem:
            self.element_tree.select_element(elem)

    def on_visibility_toggle(self, elem):
        elem.visible = not elem.visible
        self.element_tree.populate(self.elements)
        self.canvas.redraw()

    # ─── View ───────────────────────────────────────────────────────

    def toggle_grid(self):
        self.canvas.show_grid = self.grid_var.get()
        self.canvas.redraw()

    def toggle_snap(self):
        self.canvas.snap_to_grid = self.snap_var.get()

    def center_view(self):
        self.canvas.center_view()
        self.canvas.redraw()

    # ─── Undo/Redo ──────────────────────────────────────────────────

    def push_undo(self):
        state = self.elements_to_json(self.elements)
        self.undo_stack.append(json.dumps(state))
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        # Save current to redo
        current = json.dumps(self.elements_to_json(self.elements))
        self.redo_stack.append(current)
        # Restore
        state = json.loads(self.undo_stack.pop())
        self.elements = self.parse_json(state)
        self.element_tree.populate(self.elements)
        self.canvas.set_elements(self.elements)
        self.property_panel.show_element(None)

    def redo(self):
        if not self.redo_stack:
            return
        current = json.dumps(self.elements_to_json(self.elements))
        self.undo_stack.append(current)
        state = json.loads(self.redo_stack.pop())
        self.elements = self.parse_json(state)
        self.element_tree.populate(self.elements)
        self.canvas.set_elements(self.elements)
        self.property_panel.show_element(None)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = IntersectGUIEditor()
    app.run()
