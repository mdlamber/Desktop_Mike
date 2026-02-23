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
from panels.chat import ChatPanel

class TrayWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.config = load_config()
        self._setup_window()
        self._setup_transparency()
        self._setup_api()
        self._load_css()
        self._build_ui()
        self.connect('key-press-event', self._on_key_press)
        self.connect('delete-event', lambda w, e: w.hide() or True)

    def _setup_window(self):
        screen = Gdk.Screen.get_default()
        sw = screen.get_width()
        sh = screen.get_height()
        # Size: width/4 * height/2 = width*height/8
        w = sw // 4
        h = sh // 2
        self.set_default_size(w, h)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        # Position: top-right, below the GNOME top bar (~30px)
        self.move(sw - w - 8, 32)

    def _setup_transparency(self):
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect('draw', self._on_draw)

    def _on_draw(self, widget, cr):
        cr.set_source_rgba(0.039, 0.039, 0.039, 0.88)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

    def _setup_api(self):
        client = ApiClient(
            base_url=self.config.get('backend_url', 'http://localhost:3000'),
            bearer_token=self.config.get('bearer_token', ''),
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
        outer.set_margin_start(4)
        outer.set_margin_end(4)
        outer.set_margin_top(4)
        outer.set_margin_bottom(4)

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

        chat_panel = ChatPanel(self.config)
        chat_panel.set_margin_start(6)
        chat_panel.set_margin_end(6)
        chat_panel.set_margin_top(6)
        notebook.append_page(chat_panel, Gtk.Label(label='Chat'))

        # Refresh tasks/notes when their tab is switched to
        notebook.connect('switch-page', self._on_tab_switch,
                         tasks_panel, notes_panel)

        outer.pack_start(notebook, True, True, 0)
        self.add(outer)
        self.show_all()

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
            self.show_all()
            self.present()
