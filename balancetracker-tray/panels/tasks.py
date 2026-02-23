# panels/tasks.py
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

STATUS_LABELS = {
    'todo': '[todo]',
    'in_progress': '[in_progress]',
    'done': '[done]',
}

class TasksPanel(Gtk.Box):
    def __init__(self, tasks_api):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.tasks_api = tasks_api
        self.tasks = []
        self.expanded_id = None
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
        add_btn.get_style_context().add_class('accent')
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

        # Scrollable task list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.list_box)
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
        for s in ('todo', 'in_progress', 'done'):
            self.new_status.append_text(s)
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
        self.create_form.show()

    def _do_create(self, _):
        subject = self.new_subject.get_text().strip()
        if not subject:
            return
        description = self.new_description.get_text().strip() or None
        notes = self.new_notes.get_text().strip() or None
        status = self.new_status.get_active_text()
        self.create_form.hide()
        self._run_async(
            lambda: self.tasks_api.create(subject, description=description, notes=notes, status=status),
            on_success=lambda _: self.refresh(),
        )

    def refresh(self):
        self._run_async(self.tasks_api.get_all, on_success=self._on_tasks_loaded)

    def _on_tasks_loaded(self, tasks):
        self.tasks = tasks
        for child in self.list_box.get_children():
            self.list_box.remove(child)
        for task in tasks:
            row = self._build_task_row(task)
            self.list_box.add(row)
        self.list_box.show_all()

    def _build_task_row(self, task):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        outer.get_style_context().add_class('task-row')

        # Summary line
        summary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_css = f'status-{task.get("status","todo")}'
        status_lbl = Gtk.Label(label=STATUS_LABELS.get(task.get('status','todo'), ''))
        status_lbl.get_style_context().add_class(status_css)
        subject_lbl = Gtk.Label(label=task.get('subject', ''))
        subject_lbl.get_style_context().add_class('task-subject')
        subject_lbl.set_halign(Gtk.Align.START)
        subject_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END

        expand_btn = Gtk.Button(label='▸')
        expand_btn.set_relief(Gtk.ReliefStyle.NONE)

        summary.pack_start(status_lbl, False, False, 0)
        summary.pack_start(subject_lbl, True, True, 0)
        summary.pack_end(expand_btn, False, False, 0)
        outer.pack_start(summary, False, False, 0)

        # Detail section (hidden by default)
        detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        detail.set_no_show_all(True)

        if task.get('description'):
            desc_lbl = Gtk.Label(label=task['description'])
            desc_lbl.set_line_wrap(True)
            desc_lbl.set_halign(Gtk.Align.START)
            detail.pack_start(desc_lbl, False, False, 0)

        if task.get('notes'):
            notes_lbl = Gtk.Label(label=f'Notes: {task["notes"]}')
            notes_lbl.set_line_wrap(True)
            notes_lbl.set_halign(Gtk.Align.START)
            detail.pack_start(notes_lbl, False, False, 0)

        # Status change dropdown
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        combo = Gtk.ComboBoxText()
        for s in ('todo', 'in_progress', 'done'):
            combo.append_text(s)
        active_idx = {'todo': 0, 'in_progress': 1, 'done': 2}.get(task.get('status', 'todo'), 0)
        combo.set_active(active_idx)
        combo.connect('changed', lambda c, t=task: self._update_status(t['id'], c.get_active_text()))
        status_row.pack_start(Gtk.Label(label='Status:'), False, False, 0)
        status_row.pack_start(combo, True, True, 0)

        delete_btn = Gtk.Button(label='Delete')
        delete_btn.connect('clicked', lambda _, t=task: self._delete_task(t['id']))
        status_row.pack_end(delete_btn, False, False, 0)

        detail.pack_start(status_row, False, False, 0)
        outer.pack_start(detail, False, False, 0)

        def toggle_detail(_btn):
            if detail.get_visible():
                detail.hide()
                _btn.set_label('▸')
            else:
                detail.show_all()
                _btn.set_label('▾')

        expand_btn.connect('clicked', toggle_detail)
        return outer

    def _update_status(self, task_id, status):
        self._run_async(
            lambda: self.tasks_api.update(task_id, status=status),
            on_success=lambda _: self.refresh(),
        )

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
