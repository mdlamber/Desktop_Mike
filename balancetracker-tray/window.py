# window.py
import os
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
import cairo
from gi.repository import Gtk, Gdk, GLib

from config import load_config
from api.client import ApiClient
from api.tasks import TasksApi
from api.notes import NotesApi
from panels.tasks import TasksPanel
from panels.notes import NotesPanel

class TrayWindow(Gtk.Window):
    def __init__(self, token_getter):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.token_getter = token_getter
        self.config = load_config()
        self._shown_once = False
        self._setup_window()
        self._setup_transparency()
        self._setup_api()
        self._load_css()
        self._build_ui()
        self.connect('key-press-event', self._on_key_press)
        self.connect('delete-event', lambda w, e: w.hide() or True)

    def _setup_window(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geom = monitor.get_geometry()
        self._mon_x = geom.x
        self._mon_y = geom.y
        self._mon_w = geom.width
        self._mon_h = geom.height
        w = self._mon_w // 4
        h = self._mon_h // 2
        self._win_w = w
        self._win_h = h
        self.set_default_size(w, h)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_position(Gtk.WindowPosition.NONE)

    def _setup_transparency(self):
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect('draw', self._on_draw)

    def _on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

    def _setup_api(self):
        client = ApiClient(
            base_url=self.config.get('backend_url', 'http://localhost:3000'),
            token_getter=self.token_getter,
        )
        self.tasks_api = TasksApi(client)
        self.notes_api = NotesApi(client)

    def _load_css(self):
        css_path = os.path.join(os.path.dirname(__file__), 'style.css')
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.get_style_context().add_class('main-box')
        outer.set_margin_start(0)
        outer.set_margin_end(0)
        outer.set_margin_top(0)
        outer.set_margin_bottom(0)

        # Top bar with title and quit button
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        title = Gtk.Label(label='BalanceTracker')
        title.get_style_context().add_class('task-subject')
        title.set_halign(Gtk.Align.START)
        top_bar.pack_start(title, True, True, 4)

        quit_btn = Gtk.Button(label='Quit')
        quit_btn.get_style_context().add_class('flat-btn')
        quit_btn.connect('clicked', lambda _: Gtk.main_quit())
        top_bar.pack_end(quit_btn, False, False, 0)

        outer.pack_start(top_bar, False, False, 4)

        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)

        tasks_panel = TasksPanel(self.tasks_api)
        tasks_panel.set_margin_start(6)
        tasks_panel.set_margin_end(6)
        tasks_panel.set_margin_top(6)
        notebook.append_page(tasks_panel, Gtk.Label(label='Tasks'))

        notes_panel = NotesPanel(self.notes_api)
        notes_panel.set_margin_start(6)
        notes_panel.set_margin_end(6)
        notes_panel.set_margin_top(6)
        notebook.append_page(notes_panel, Gtk.Label(label='Notes'))

        notebook.connect('switch-page', self._on_tab_switch,
                         tasks_panel, notes_panel)

        outer.pack_start(notebook, True, True, 0)
        self.add(outer)

    def _on_tab_switch(self, notebook, page, page_num, tasks_panel, notes_panel):
        if page_num == 0:
            tasks_panel.refresh()
        elif page_num == 1:
            notes_panel.refresh()

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            # Position top-right, below GNOME top bar
            x = self._mon_x + self._mon_w - self._win_w - 8
            y = self._mon_y + 32
            self.move(x, y)
            if not self._shown_once:
                self.show_all()
                self._shown_once = True
            else:
                self.show()
            self.move(x, y)
            self.present()
