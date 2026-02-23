# panels/notes.py
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class NotesPanel(Gtk.Box):
    def __init__(self, notes_api):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.notes_api = notes_api
        self.notes = []
        self.selected_note = None
        self._save_timer = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label = Gtk.Label(label='Notes')
        label.set_halign(Gtk.Align.START)
        header.pack_start(label, True, True, 0)
        add_btn = Gtk.Button(label='+')
        add_btn.get_style_context().add_class('accent')
        add_btn.connect('clicked', self._create_note_dialog)
        header.pack_end(add_btn, False, False, 0)
        self.pack_start(header, False, False, 4)

        # Error label
        self.error_label = Gtk.Label(label='')
        self.error_label.get_style_context().add_class('error-bar')
        self.error_label.set_no_show_all(True)
        self.pack_start(self.error_label, False, False, 0)

        # Two-pane layout
        paned = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.pack_start(paned, True, True, 0)

        # Left: note list (fixed width)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_size_request(140, -1)
        scroll_left = Gtk.ScrolledWindow()
        scroll_left.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.notes_listbox = Gtk.ListBox()
        self.notes_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.notes_listbox.connect('row-selected', self._on_note_selected)
        scroll_left.add(self.notes_listbox)
        left.pack_start(scroll_left, True, True, 0)
        paned.pack_start(left, False, False, 0)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        paned.pack_start(sep, False, False, 0)

        # Right: content editor
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.content_label = Gtk.Label(label='Select a note')
        self.content_label.set_halign(Gtk.Align.CENTER)
        self.content_label.set_valign(Gtk.Align.CENTER)

        scroll_right = Gtk.ScrolledWindow()
        scroll_right.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.content_view = Gtk.TextView()
        self.content_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.content_view.get_buffer().connect('changed', self._on_content_changed)
        self.content_view.set_sensitive(False)
        scroll_right.add(self.content_view)

        self.delete_btn = Gtk.Button(label='Delete Note')
        self.delete_btn.connect('clicked', self._delete_selected)
        self.delete_btn.set_sensitive(False)

        right.pack_start(scroll_right, True, True, 0)
        right.pack_start(self.delete_btn, False, False, 0)
        paned.pack_start(right, True, True, 0)

    def refresh(self):
        def do_fetch():
            try:
                notes = self.notes_api.get_all()
                GLib.idle_add(self._on_notes_loaded, notes)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
        threading.Thread(target=do_fetch, daemon=True).start()

    def _on_notes_loaded(self, notes):
        self.notes = notes
        for child in self.notes_listbox.get_children():
            self.notes_listbox.remove(child)
        for note in notes:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class('note-row')
            lbl = Gtk.Label(label=note.get('title', ''))
            lbl.set_halign(Gtk.Align.START)
            lbl.set_ellipsize(3)
            lbl.set_xalign(0)
            lbl.set_padding(6, 4)
            row.add(lbl)
            row.note_data = note
            self.notes_listbox.add(row)
        self.notes_listbox.show_all()

    def _on_note_selected(self, _listbox, row):
        if row is None:
            self.selected_note = None
            self.content_view.set_sensitive(False)
            self.delete_btn.set_sensitive(False)
            return
        self.selected_note = row.note_data
        buf = self.content_view.get_buffer()
        buf.handler_block_by_func(self._on_content_changed)
        buf.set_text(self.selected_note.get('content') or '')
        buf.handler_unblock_by_func(self._on_content_changed)
        self.content_view.set_sensitive(True)
        self.delete_btn.set_sensitive(True)

    def _on_content_changed(self, buf):
        if self.selected_note is None:
            return
        if self._save_timer:
            GLib.source_remove(self._save_timer)
        self._save_timer = GLib.timeout_add(1500, self._auto_save)

    def _auto_save(self):
        self._save_timer = None
        if self.selected_note is None:
            return False
        buf = self.content_view.get_buffer()
        content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        note_id = self.selected_note['id']
        def do_save():
            try:
                self.notes_api.update(note_id, content=content)
                GLib.idle_add(self.error_label.hide)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
        threading.Thread(target=do_save, daemon=True).start()
        return False

    def _create_note_dialog(self, _):
        dialog = Gtk.Dialog(title='New Note', modal=True)
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Create', Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_placeholder_text('Note title')
        dialog.get_content_area().pack_start(entry, False, False, 8)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            title = entry.get_text().strip()
            if title:
                def do_create():
                    try:
                        self.notes_api.create(title)
                        GLib.idle_add(self.refresh)
                    except Exception as e:
                        GLib.idle_add(self._show_error, str(e))
                threading.Thread(target=do_create, daemon=True).start()
        dialog.destroy()

    def _delete_selected(self, _):
        if self.selected_note is None:
            return
        note_id = self.selected_note['id']
        self.selected_note = None
        self.content_view.set_sensitive(False)
        self.delete_btn.set_sensitive(False)
        def do_delete():
            try:
                self.notes_api.delete(note_id)
                GLib.idle_add(self.refresh)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
        threading.Thread(target=do_delete, daemon=True).start()

    def _show_error(self, msg):
        self.error_label.set_text(msg)
        self.error_label.show()
