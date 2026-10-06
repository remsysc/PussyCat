"""GUI for PussyCat IDE.

tkinter-based desktop interface for code editing, execution, and output display.
"""

import tkinter as tk
from tkinter import ttk
from lexer import tokenize
from transpiler import transpile
from executor import execute
from constants import KEYWORD_MAP

# ── Cat Theme Palette (warm light) ───────────────────────────────────────────
CAT = {
    "bg_dark":      "#fdf6ee",   # warm ivory – main background
    "bg_panel":     "#fef9f4",   # softer ivory – editor / output panel
    "bg_bar":       "#f2dfd0",   # warm rose-tan – keyword bar & status bar
    "bg_splash":    "#fdf6ee",   # same as main bg for splash
    "accent":       "#c0445a",   # deep rose – primary accent (readable on light)
    "accent2":      "#d4782a",   # warm amber – cursor / running indicator
    "fg_main":      "#2e2014",   # dark espresso – main editor text
    "fg_dim":       "#a08878",   # warm taupe – line numbers / hints
    "fg_keyword":   "#7b3f6e",   # dusty plum – keyword bar labels
    "success":      "#2e7d32",   # forest green – success state
    "error":        "#b71c1c",   # deep red – error state
    "python_hdr":   "#1565c0",   # navy – python section header
    "output_hdr":   "#d4782a",   # amber – output section header
    "error_hdr":    "#b71c1c",   # deep red – error section header
    "sash":         "#e8cfc0",   # light rose-tan – pane divider
    "cursor":       "#c0445a",   # deep rose – text cursor
    "line_num_bg":  "#f2e8de",   # slightly warmer than panel – line number gutter
    "editor_hl":    "#c0445a",   # focus highlight border on editor
    "select_bg":    "#f2b8c6",   # soft pink – text selection background
    "select_fg":    "#2e2014",   # espresso – text selection foreground
}

FONT_MONO  = ("Courier New", 11)
FONT_SMALL = ("Courier New",  9)
FONT_BOLD  = ("Courier New", 10, "bold")
FONT_BIG   = ("Courier New", 22, "bold")

# Splash frames: each is (emoji_string, delay_ms)
SPLASH_FRAMES = [
    ("🐱  PussyCat IDE  🐱",        0),
    ("😺  Loading…  😺",           420),
    ("😸  Almost there…  😸",      840),
    ("🐾  Meow!  🐾",             1260),
    ("✨  Welcome, hacker!  ✨",   1680),
]
SPLASH_TOTAL_MS = 2200   # splash closes after this


class PussyCatIDE:
    """Main IDE window with split-panel layout."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._apply_cat_theme()       # #33
        self._create_widgets()
        self._show_splash()           # #34

    # ── #33  Cat theme ────────────────────────────────────────────────────────
    def _apply_cat_theme(self):
        """Configure root window with cat theme."""
        self.root.title("🐱 PussyCat IDE 🐾")
        self.root.geometry("1200x800")
        self.root.configure(bg=CAT["bg_dark"])
        # Give the title-bar icon a paw-print via iconphoto (emoji fallback)
        try:
            icon = tk.PhotoImage(width=1, height=1)
            self.root.iconphoto(True, icon)
        except Exception:
            pass

    # ── #34  Splash screen ────────────────────────────────────────────────────
    def _show_splash(self):
        """Show a 2-second animated emoji splash screen."""
        self._splash = tk.Toplevel(self.root)
        splash = self._splash
        splash.overrideredirect(True)           # no title bar
        splash.configure(bg=CAT["bg_splash"])
        splash.attributes("-topmost", True)

        # Centre on screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 420, 220
        splash.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # Border frame for a little style
        border = tk.Frame(splash, bg=CAT["accent"], bd=0)
        border.place(relwidth=1, relheight=1)
        inner = tk.Frame(border, bg=CAT["bg_splash"], bd=0)
        inner.place(x=2, y=2, relwidth=1, relheight=1, width=-4, height=-4)

        self._splash_label = tk.Label(
            inner,
            text="",
            bg=CAT["bg_splash"],
            fg=CAT["fg_main"],
            font=FONT_BIG,
            justify=tk.CENTER,
        )
        self._splash_label.place(relx=0.5, rely=0.45, anchor=tk.CENTER)

        self._splash_sub = tk.Label(
            inner,
            text="a cat-themed programming language 🐾",
            bg=CAT["bg_splash"],
            fg=CAT["fg_dim"],
            font=FONT_SMALL,
        )
        self._splash_sub.place(relx=0.5, rely=0.72, anchor=tk.CENTER)

        # Kick off frame animation
        for text, delay in SPLASH_FRAMES:
            self.root.after(delay, lambda t=text: self._splash_label.config(text=t))

        # Close splash and focus editor
        self.root.after(SPLASH_TOTAL_MS, self._close_splash)

    def _close_splash(self):
        if self._splash and self._splash.winfo_exists():
            self._splash.destroy()
        self.editor.focus_set()

    # ── Widget construction ───────────────────────────────────────────────────
    def _create_widgets(self):
        """Create all GUI widgets."""
        # ── Keyword bar ───────────────────────────────────────────────────────
        self.keyword_bar = tk.Frame(self.root, bg=CAT["bg_bar"], height=40)
        self.keyword_bar.pack(side=tk.TOP, fill=tk.X)

        # ── Main split pane ───────────────────────────────────────────────────
        self.main_pane = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            sashwidth=5,
            sashrelief=tk.FLAT,
            bg=CAT["sash"],
        )
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # Left frame (editor)
        self.left_frame = tk.Frame(self.main_pane, bg=CAT["bg_panel"])
        self.main_pane.add(self.left_frame, minsize=400)

        self.panel_label_left = tk.Label(
            self.left_frame,
            text="🐾  YOUR CODE",
            bg=CAT["bg_panel"],
            fg=CAT["accent"],
            font=FONT_BOLD,
        )
        self.panel_label_left.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        self.editor_frame = tk.Frame(self.left_frame, bg=CAT["bg_panel"])
        self.editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.line_numbers = tk.Text(
            self.editor_frame,
            width=4,
            state="disabled",
            bg=CAT["line_num_bg"],
            fg=CAT["fg_dim"],
            font=FONT_MONO,
            takefocus=0,
            highlightthickness=0,
            bd=0,
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # #27 — scrollbar shared between editor and line numbers
        self.editor_scrollbar = tk.Scrollbar(self.editor_frame, orient=tk.VERTICAL)
        self.editor_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.editor = tk.Text(
            self.editor_frame,
            bg=CAT["bg_dark"],
            fg=CAT["fg_main"],
            insertbackground=CAT["cursor"],
            font=FONT_MONO,
            undo=True,
            wrap=tk.NONE,
            highlightthickness=1,
            highlightcolor=CAT["editor_hl"],
            highlightbackground=CAT["bg_panel"],
            bd=0,
            selectbackground=CAT["select_bg"],
            selectforeground=CAT["select_fg"],
            yscrollcommand=self._on_editor_scroll,
        )
        self.editor.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.editor_scrollbar.config(command=self.editor.yview)

        # Right frame (output)
        self.right_frame = tk.Frame(self.main_pane, bg=CAT["bg_panel"])
        self.main_pane.add(self.right_frame, minsize=400)

        self.panel_label_right = tk.Label(
            self.right_frame,
            text="😺  OUTPUT",
            bg=CAT["bg_panel"],
            fg=CAT["accent"],
            font=FONT_BOLD,
        )
        self.panel_label_right.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        self.output = tk.Text(
            self.right_frame,
            state="disabled",
            bg=CAT["bg_dark"],
            fg=CAT["fg_main"],
            font=FONT_MONO,
            wrap=tk.WORD,
            highlightthickness=0,
            bd=0,
            selectbackground=CAT["select_bg"],
            selectforeground=CAT["select_fg"],
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure output text tags  (#30 — color tags per Sprint-3 spec)
        self.output.tag_config("python_header", foreground=CAT["python_hdr"], font=FONT_BOLD)
        self.output.tag_config("output_header", foreground=CAT["output_hdr"], font=FONT_BOLD)
        self.output.tag_config("error_header",  foreground=CAT["error_hdr"],  font=FONT_BOLD)
        self.output.tag_config("python_body",   foreground=CAT["fg_main"],    font=FONT_MONO)
        self.output.tag_config("output_body",   foreground=CAT["fg_main"],    font=FONT_MONO)
        self.output.tag_config("error_body",    foreground=CAT["error_hdr"],  font=FONT_MONO)
        self.output.tag_config("separator",     foreground=CAT["fg_dim"],     font=FONT_SMALL)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status_bar = tk.Frame(self.root, bg=CAT["bg_bar"], height=36)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # #3 — Run button (left side of status bar)
        self.run_btn = tk.Button(
            self.status_bar,
            text="▶  Run",
            command=self.run_pipeline,
            bg=CAT["accent"],
            fg="#ffffff",
            activebackground=CAT["accent2"],
            activeforeground="#ffffff",
            font=FONT_BOLD,
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=4,
            bd=0,
        )
        self.run_btn.pack(side=tk.LEFT, padx=10, pady=4)

        # Hint label
        tk.Label(
            self.status_bar,
            text="Ctrl+Enter to run  •  Tab = 4 spaces",
            bg=CAT["bg_bar"],
            fg=CAT["fg_dim"],
            font=FONT_SMALL,
        ).pack(side=tk.LEFT, padx=4)

        self.status_label = tk.Label(
            self.status_bar,
            text="🐱 ready",
            bg=CAT["bg_bar"],
            fg=CAT["fg_dim"],
            font=FONT_SMALL,
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # ── Bindings ──────────────────────────────────────────────────────────
        self.editor.bind("<Tab>",           self._on_tab)
        self.editor.bind("<Control-Return>", self._on_ctrl_enter)
        self.editor.bind("<KeyRelease>",    self._on_key_release)
        self.editor.bind("<<Modified>>",    self._on_modified)

        self._update_line_numbers()
        self._fill_keyword_bar()

    # ── Keyword bar ───────────────────────────────────────────────────────────
    def _fill_keyword_bar(self):
        """Fill keyword bar with one button per KEYWORD_MAP entry ("meow → if").

        Clicking a button inserts the PussyCat keyword at the editor cursor.
        """
        self.keyword_buttons: dict[str, tk.Button] = {}
        columns = 10
        for i, (cat_kw, py_kw) in enumerate(KEYWORD_MAP.items()):
            btn = tk.Button(
                self.keyword_bar,
                text=f"{cat_kw} → {py_kw}",
                command=lambda k=cat_kw: self._insert_keyword(k),
                bg=CAT["bg_panel"],
                fg=CAT["fg_keyword"],
                activebackground=CAT["select_bg"],
                activeforeground=CAT["accent"],
                font=FONT_SMALL,
                relief=tk.FLAT,
                cursor="hand2",
                padx=6,
                pady=2,
                bd=0,
            )
            btn.grid(row=i // columns, column=i % columns, padx=2, pady=2, sticky="ew")
            self.keyword_buttons[cat_kw] = btn
        for c in range(columns):
            self.keyword_bar.grid_columnconfigure(c, weight=1, uniform="kw")

    def _insert_keyword(self, keyword: str):
        """Insert a keyword from the bar into the editor at cursor."""
        self.editor.insert(tk.INSERT, keyword + " ")
        self.editor.focus_set()

    # ── Event handlers ────────────────────────────────────────────────────────
    def _on_tab(self, event):
        self.editor.insert(tk.INSERT, "    ")
        return "break"

    def _on_ctrl_enter(self, event):
        self.run_pipeline()
        return "break"

    def _on_key_release(self, event):
        self._update_line_numbers()

    def _on_modified(self, event):
        if self.editor.edit_modified():
            self._update_line_numbers()
            self.editor.edit_modified(False)

    def _on_editor_scroll(self, *args):
        """#27 — forward scroll position to both scrollbar and line numbers."""
        self.editor_scrollbar.set(*args)
        self.line_numbers.yview_moveto(args[0])

    def _update_line_numbers(self):
        line_count = int(self.editor.index("end-1c").split(".")[0])
        new_lines = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        self.line_numbers.insert("1.0", new_lines)
        self.line_numbers.config(state="disabled")
        # #27 — keep line numbers scrolled in sync with the editor
        self.line_numbers.yview_moveto(self.editor.yview()[0])

    # ── Run pipeline ──────────────────────────────────────────────────────────
    def run_pipeline(self):
        """Execute the full run pipeline: tokenize → transpile → execute."""
        self.update_status("running")
        self._set_run_button_state("running")

        # Clear output pane before each run
        self.output.config(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.config(state="disabled")

        source = self.editor.get("1.0", tk.END).strip()

        # ── Tokenize ──────────────────────────────────────────────────────────
        result = tokenize(source)
        if result.error:
            self.display_error(result.error)
            self.update_status("error")
            self._set_run_button_state("ready")
            self._animate_error()
            return

        # ── Transpile ─────────────────────────────────────────────────────────
        transpile_result = transpile(result.tokens)
        self.display_python(transpile_result.python)

        # ── Execute ───────────────────────────────────────────────────────────
        exec_result = execute(transpile_result.python, transpile_result.line_map)

        if exec_result.timed_out:
            self.display_error(exec_result.error)
            self.update_status("error")
            self._set_run_button_state("ready")
            self._animate_error()
            return

        if exec_result.stdout:
            self.display_output(exec_result.stdout)

        if exec_result.error:
            # show the full remapped traceback from stderr
            self.display_error(exec_result.error)
            self.update_status("error")
            self._set_run_button_state("ready")
            self._animate_error()
        else:
            self.update_status("ok")
            self._set_run_button_state("ready")
            self._animate_success()

    # ── Status bar ────────────────────────────────────────────────────────────
    def _set_run_button_state(self, state: str):
        """Disable run button while pipeline is running, re-enable after."""
        if state == "running":
            self.run_btn.config(
                state=tk.DISABLED,
                text="⏳ Running…",
                bg=CAT["fg_dim"],
            )
        else:
            self.run_btn.config(
                state=tk.NORMAL,
                text="▶  Run",
                bg=CAT["accent"],
            )

    def update_status(self, status: str):
        cfg = {
            "ready":   ("🐱 ready",      CAT["fg_dim"]),
            "running": ("⚡ running…",   CAT["accent2"]),
            "ok":      ("✅ ok",          CAT["success"]),
            "error":   ("❌ error",       CAT["error"]),
        }
        text, color = cfg.get(status, cfg["ready"])
        self.status_label.config(text=text, fg=color)

    # ── Output display (#30) ──────────────────────────────────────────────────
    def display_python(self, python_code: str):
        """Display generated Python code with navy header + mono body."""
        self.output.config(state="normal")
        self.output.insert(tk.END, "── 🐍 Generated Python ──\n", "python_header")
        self.output.insert(tk.END, python_code + "\n", "python_body")
        self.output.insert(tk.END, "\n", "separator")
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def display_output(self, output: str):
        """Display execution stdout with amber header + mono body."""
        self.output.config(state="normal")
        self.output.insert(tk.END, "── 😺 Output ──\n", "output_header")
        self.output.insert(tk.END, output + "\n", "output_body")
        self.output.insert(tk.END, "\n", "separator")
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def display_error(self, error: str):
        """Display error/traceback with red header + red mono body."""
        self.output.config(state="normal")
        self.output.insert(tk.END, "── 🙀 Error ──\n", "error_header")
        self.output.insert(tk.END, error + "\n", "error_body")
        self.output.insert(tk.END, "\n", "separator")
        self.output.see(tk.END)
        self.output.config(state="disabled")

    # ── #35  Success animation ────────────────────────────────────────────────
    def _animate_success(self):
        """Flash green hearts in the status bar then fade back."""
        frames = [
            ("💚 💚 💚  ok  💚 💚 💚", CAT["success"]),
            ("💛 ✨  ok  ✨ 💛",        CAT["accent2"]),
            ("💚  ok  💚",              CAT["success"]),
            ("✅ ok",                   CAT["success"]),
        ]
        self._play_status_frames(frames, interval=160)
        self._pulse_panel(self.output, "#c8f0cb", CAT["bg_dark"], steps=6, interval=80)

    # ── #36  Error animation ──────────────────────────────────────────────────
    def _animate_error(self):
        """Shake the window and flash red in the status bar."""
        self._shake_window()
        frames = [
            ("🙀 ERROR 🙀",  CAT["error"]),
            ("❗ error ❗",  CAT["error"]),
            ("🙀 ERROR 🙀",  CAT["error"]),
            ("❌ error",      CAT["error"]),
        ]
        self._play_status_frames(frames, interval=160)
        self._pulse_panel(self.output, "#ffd0d0", CAT["bg_dark"], steps=6, interval=80)

    # ── Animation helpers ─────────────────────────────────────────────────────
    def _play_status_frames(self, frames, interval=150):
        """Cycle status label through a list of (text, color) frames."""
        def _step(i=0):
            if i < len(frames):
                text, color = frames[i]
                self.status_label.config(text=text, fg=color)
                self.root.after(interval, lambda: _step(i + 1))
        _step()

    def _pulse_panel(self, widget, color_on, color_off, steps=6, interval=70):
        """Rapidly toggle widget background between two colours."""
        colors = ([color_on, color_off] * (steps // 2))
        def _step(i=0):
            if i < len(colors):
                widget.config(bg=colors[i])
                self.root.after(interval, lambda: _step(i + 1))
            else:
                widget.config(bg=color_off)
        _step()

    def _shake_window(self, shakes=6, distance=8, interval=40):
        """Shake the root window horizontally."""
        x0 = self.root.winfo_x()
        y0 = self.root.winfo_y()
        offsets = []
        for i in range(shakes):
            offsets.append(distance if i % 2 == 0 else -distance)
        offsets.append(0)  # return to original

        def _step(i=0):
            if i < len(offsets):
                self.root.geometry(f"+{x0 + offsets[i]}+{y0}")
                self.root.after(interval, lambda: _step(i + 1))
        _step()

    # ── Misc ──────────────────────────────────────────────────────────────────
    def clear(self):
        self.editor.delete("1.0", tk.END)
        self.output.config(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.config(state="disabled")
        self.update_status("ready")


def main():
    """Entry point for the IDE."""
    root = tk.Tk()
    app = PussyCatIDE(root)
    root.mainloop()


if __name__ == "__main__":
    main()
