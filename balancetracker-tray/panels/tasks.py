# panels/tasks.py
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

STATUS_COLORS = {
    'todo': '#888888',
    'in_progress': '#FFD600',
    'done': '#00C853',
}
STATUS_ICONS = {
    'todo': '\u25cb',       # ○
    'in_progress': '\u25d4', # ◔
    'done': '\u25cf',        # ●
}
STATUS_DISPLAY = {
    'todo': 'Todo',
    'in_progress': 'In Progress',
    'done': 'Complete',
}
STATUS_VALUES = ['todo', 'in_progress', 'done']

class TasksPanel(Gtk.Box):
    def __init__(self, tasks_api):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.tasks_api = tasks_api
        self.tasks = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header bar with title and add button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label = Gtk.Label(label='Tasks')
        label.get_style_context().add_class('task-subject')
        label.set_halign(Gtk.Align.START)
        header.pack_start(label, True, True, 0)
        add_btn = Gtk.Button(label='+')
        add_btn.get_style_context().add_class('flat-btn')
        add_btn.get_style_context().add_class('add-btn')
        add_btn.connect('clicked', self._show_create_form)
        header.pack_end(add_btn, False, False, 0)
        self.pack_start(header, False, False, 4)

        # Error label (hidden by default)
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
        self.empty_label = Gtk.Label(label='No tasks yet. Click + to create one.')
        self.empty_label.set_opacity(0.5)
        self.empty_label.set_no_show_all(True)
        self.pack_start(self.empty_label, False, False, 8)

        # Scrollable task list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.task_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroll.add(self.task_list)
        self.pack_start(scroll, True, True, 0)

    def _build_create_form(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.get_style_context().add_class('task-row')

        self.new_subject = Gtk.Entry()
        self.new_subject.set_placeholder_text('Subject (required)')
        box.pack_start(self.new_subject, False, False, 0)

        self.new_description = Gtk.Entry()
        self.new_description.set_placeholder_text('Description')
        box.pack_start(self.new_description, False, False, 0)

        self.new_notes = Gtk.Entry()
        self.new_notes.set_placeholder_text('Notes')
        box.pack_start(self.new_notes, False, False, 0)

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        status_label = Gtk.Label(label='Status:')
        self.new_status = Gtk.ComboBoxText()
        for s in STATUS_VALUES:
            self.new_status.append_text(STATUS_DISPLAY[s])
        self.new_status.set_active(0)
        status_box.pack_start(status_label, False, False, 0)
        status_box.pack_start(self.new_status, True, True, 0)
        box.pack_start(status_box, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        save_btn = Gtk.Button(label='Save')
        save_btn.get_style_context().add_class('accent')
        save_btn.connect('clicked', self._do_create)
        cancel_btn = Gtk.Button(label='Cancel')
        cancel_btn.connect('clicked', lambda _: self.create_form.hide())
        btn_box.pack_start(save_btn, True, True, 0)
        btn_box.pack_start(cancel_btn, True, True, 0)
        box.pack_start(btn_box, False, False, 0)

        return box

    def _show_create_form(self, _):
        self.new_subject.set_text('')
        self.new_description.set_text('')
        self.new_notes.set_text('')
        self.new_status.set_active(0)
        self.create_form.show_all()

    def _do_create(self, _):
        subject = self.new_subject.get_text().strip()
        if not subject:
            return
        description = self.new_description.get_text().strip() or None
        notes = self.new_notes.get_text().strip() or None
        status = STATUS_VALUES[self.new_status.get_active()]
        self.create_form.hide()
        self._run_async(
            lambda: self.tasks_api.create(subject, description=description, notes=notes, status=status),
            on_success=lambda _: self.refresh(),
        )

    def refresh(self):
        self._run_async(self.tasks_api.get_all, on_success=self._on_tasks_loaded)

    def _on_tasks_loaded(self, tasks):
        self.spinner.stop()
        self.spinner.hide()
        self.tasks = tasks
        self._details = []
        for child in self.task_list.get_children():
            self.task_list.remove(child)
        for task in tasks:
            row, detail = self._build_task_row(task)
            self.task_list.pack_start(row, False, False, 0)
            self._details.append(detail)
        if tasks:
            self.empty_label.hide()
        else:
            self.empty_label.show()

        self.task_list.show_all()
        for d in self._details:
            d.hide()
        self.create_form.hide()
        self.error_label.hide()

    def _build_task_row(self, task):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        outer.get_style_context().add_class('task-row')

        # Summary line
        summary_btn = Gtk.Button()
        summary_btn.set_relief(Gtk.ReliefStyle.NONE)
        summary_btn.get_style_context().add_class('task-summary')
        summary_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        status = task.get('status', 'todo')
        color = STATUS_COLORS.get(status, '#888888')
        icon = STATUS_ICONS.get(status, '\u25cb')
        status_lbl = Gtk.Label()
        status_lbl.set_markup(f'<span foreground="{color}">{icon}</span>')

        display_text = task.get('subject') or task.get('description') or '(untitled)'
        subject_lbl = Gtk.Label(label=display_text)
        subject_lbl.get_style_context().add_class('task-subject')
        subject_lbl.set_halign(Gtk.Align.START)
        subject_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END

        arrow_lbl = Gtk.Label(label='▸')

        summary_box.pack_start(status_lbl, False, False, 0)
        summary_box.pack_start(subject_lbl, True, True, 0)
        summary_box.pack_end(arrow_lbl, False, False, 0)
        summary_btn.add(summary_box)
        outer.pack_start(summary_btn, False, False, 0)

        # Editable detail section (hidden by default)
        detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        subject_entry = Gtk.Entry()
        subject_entry.set_text(task.get('subject', ''))
        subject_entry.set_placeholder_text('Subject')
        detail.pack_start(subject_entry, False, False, 0)

        desc_entry = Gtk.Entry()
        desc_entry.set_text(task.get('description', '') or '')
        desc_entry.set_placeholder_text('Description')
        detail.pack_start(desc_entry, False, False, 0)

        notes_entry = Gtk.Entry()
        notes_entry.set_text(task.get('notes', '') or '')
        notes_entry.set_placeholder_text('Notes')
        detail.pack_start(notes_entry, False, False, 0)

        # Status and action buttons
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        combo = Gtk.ComboBoxText()
        for s in STATUS_VALUES:
            combo.append_text(STATUS_DISPLAY[s])
        active_idx = STATUS_VALUES.index(task.get('status', 'todo')) if task.get('status', 'todo') in STATUS_VALUES else 0
        combo.set_active(active_idx)
        status_row.pack_start(Gtk.Label(label='Status:'), False, False, 0)
        status_row.pack_start(combo, True, True, 0)
        detail.pack_start(status_row, False, False, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        save_btn = Gtk.Button(label='Save')
        save_btn.get_style_context().add_class('flat-btn')
        delete_btn = Gtk.Button(label='Delete')
        delete_btn.get_style_context().add_class('flat-btn')

        def do_save(_):
            fields = {
                'subject': subject_entry.get_text().strip(),
                'description': desc_entry.get_text().strip() or None,
                'notes': notes_entry.get_text().strip() or None,
                'status': STATUS_VALUES[combo.get_active()],
            }
            self._run_async(
                lambda: self.tasks_api.update(task['id'], **fields),
                on_success=lambda _: self.refresh(),
            )

        save_btn.connect('clicked', do_save)
        delete_btn.connect('clicked', lambda _, t=task: self._delete_task(t['id']))

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

    def _delete_task(self, task_id):
        self._run_async(
            lambda: self.tasks_api.delete(task_id),
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
