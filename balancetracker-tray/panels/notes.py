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
        self._details = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label = Gtk.Label(label='Notes')
        label.get_style_context().add_class('task-subject')
        label.set_halign(Gtk.Align.START)
        header.pack_start(label, True, True, 0)
        add_btn = Gtk.Button(label='+')
        add_btn.get_style_context().add_class('flat-btn')
        add_btn.get_style_context().add_class('add-btn')
        add_btn.connect('clicked', self._show_create_form)
        header.pack_end(add_btn, False, False, 0)
        self.pack_start(header, False, False, 4)

        # Error label
        self.error_label = Gtk.Label(label='')
        self.error_label.get_style_context().add_class('error-bar')
        self.error_label.set_no_show_all(True)
        self.pack_start(self.error_label, False, False, 0)

        # Create form (hidden by default)
        self.create_form = self._build_create_form()
        self.create_form.set_no_show_all(True)
        self.pack_start(self.create_form, False, False, 0)

        # Loading spinner
        self.spinner = Gtk.Spinner()
        self.spinner.start()
        self.pack_start(self.spinner, False, False, 8)

        # Empty state label
        self.empty_label = Gtk.Label(label='No notes yet. Click + to create one.')
        self.empty_label.set_opacity(0.5)
        self.empty_label.set_no_show_all(True)
        self.pack_start(self.empty_label, False, False, 8)

        # Scrollable note list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.note_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroll.add(self.note_list)
        self.pack_start(scroll, True, True, 0)

    def _build_create_form(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.get_style_context().add_class('task-row')

        self.new_title = Gtk.Entry()
        self.new_title.set_placeholder_text('Title (required)')
        box.pack_start(self.new_title, False, False, 0)

        self.new_content = Gtk.Entry()
        self.new_content.set_placeholder_text('Content')
        box.pack_start(self.new_content, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        save_btn = Gtk.Button(label='Save')
        save_btn.get_style_context().add_class('flat-btn')
        save_btn.connect('clicked', self._do_create)
        cancel_btn = Gtk.Button(label='Cancel')
        cancel_btn.get_style_context().add_class('flat-btn')
        cancel_btn.connect('clicked', lambda _: self.create_form.hide())
        btn_box.pack_start(save_btn, True, True, 0)
        btn_box.pack_start(cancel_btn, True, True, 0)
        box.pack_start(btn_box, False, False, 0)

        return box

    def _show_create_form(self, _):
        self.new_title.set_text('')
        self.new_content.set_text('')
        self.create_form.show_all()

    def _do_create(self, _):
        title = self.new_title.get_text().strip()
        if not title:
            return
        content = self.new_content.get_text().strip() or None
        self.create_form.hide()
        self._run_async(
            lambda: self.notes_api.create(title, content=content),
            on_success=lambda _: self.refresh(),
        )

    def refresh(self):
        self._run_async(self.notes_api.get_all, on_success=self._on_notes_loaded)

    def _on_notes_loaded(self, notes):
        self.spinner.stop()
        self.spinner.hide()
        self.notes = notes
        self._details = []
        for child in self.note_list.get_children():
            self.note_list.remove(child)

        if notes:
            self.empty_label.hide()
        else:
            self.empty_label.show()

        for note in notes:
            row, detail = self._build_note_row(note)
            self.note_list.pack_start(row, False, False, 0)
            self._details.append(detail)
        self.note_list.show_all()
        for d in self._details:
            d.hide()
        self.create_form.hide()
        self.error_label.hide()

    def _build_note_row(self, note):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        outer.get_style_context().add_class('task-row')

        # Summary line
        summary_btn = Gtk.Button()
        summary_btn.set_relief(Gtk.ReliefStyle.NONE)
        summary_btn.get_style_context().add_class('task-summary')
        summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        # Title row with arrow
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        display_text = note.get('title') or '(untitled)'
        title_lbl = Gtk.Label(label=display_text)
        title_lbl.get_style_context().add_class('task-subject')
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.set_ellipsize(3)

        arrow_lbl = Gtk.Label(label='▸')
        title_row.pack_start(title_lbl, True, True, 0)
        title_row.pack_end(arrow_lbl, False, False, 0)
        summary_box.pack_start(title_row, False, False, 0)

        # Content preview
        content = note.get('content') or ''
        if content:
            preview = content[:80].replace('\n', ' ')
            if len(content) > 80:
                preview += '...'
            preview_lbl = Gtk.Label(label=preview)
            preview_lbl.set_halign(Gtk.Align.START)
            preview_lbl.set_ellipsize(3)
            preview_lbl.set_opacity(0.6)
            summary_box.pack_start(preview_lbl, False, False, 0)

        summary_btn.add(summary_box)
        outer.pack_start(summary_btn, False, False, 0)

        # Editable detail section
        detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        title_entry = Gtk.Entry()
        title_entry.set_text(note.get('title', ''))
        title_entry.set_placeholder_text('Title')
        detail.pack_start(title_entry, False, False, 0)

        content_entry = Gtk.Entry()
        content_entry.set_text(note.get('content') or '')
        content_entry.set_placeholder_text('Content')
        detail.pack_start(content_entry, False, False, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        save_btn = Gtk.Button(label='Save')
        save_btn.get_style_context().add_class('flat-btn')
        delete_btn = Gtk.Button(label='Delete')
        delete_btn.get_style_context().add_class('flat-btn')

        def do_save(_):
            fields = {
                'title': title_entry.get_text().strip(),
                'content': content_entry.get_text().strip() or None,
            }
            self._run_async(
                lambda: self.notes_api.update(note['id'], **fields),
                on_success=lambda _: self.refresh(),
            )

        save_btn.connect('clicked', do_save)
        delete_btn.connect('clicked', lambda _, n=note: self._delete_note(n['id']))

        btn_row.pack_start(save_btn, True, True, 0)
        btn_row.pack_start(delete_btn, True, True, 0)
        detail.pack_start(btn_row, False, False, 0)

        outer.pack_start(detail, False, False, 0)

        def toggle_detail(_btn):
            if detail.get_visible():
                detail.hide()
                arrow_lbl.set_text('▸')
            else:
                detail.show_all()
                arrow_lbl.set_text('▾')

        summary_btn.connect('clicked', toggle_detail)
        return outer, detail

    def _delete_note(self, note_id):
        self._run_async(
            lambda: self.notes_api.delete(note_id),
            on_success=lambda _: self.refresh(),
        )

    def _run_async(self, fn, on_success=None):
        def worker():
            try:
                result = fn()
                if on_success:
                    GLib.idle_add(on_success, result)
                GLib.idle_add(self.error_label.hide)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _show_error(self, msg):
        self.error_label.set_text(msg)
        self.error_label.show()
