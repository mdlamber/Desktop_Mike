# panels/chat.py
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import anthropic

class ChatPanel(Gtk.Box):
    def __init__(self, config: dict):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.config = config
        self.history = []  # list of {"role": "user"|"assistant", "content": "..."}
        self._build_ui()

    def _build_ui(self):
        # Header
        header = Gtk.Label(label='Claude Chat')
        header.set_halign(Gtk.Align.START)
        self.pack_start(header, False, False, 4)

        # Error label
        self.error_label = Gtk.Label(label='')
        self.error_label.get_style_context().add_class('error-bar')
        self.error_label.set_no_show_all(True)
        self.pack_start(self.error_label, False, False, 0)

        # Chat history scroll area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.history_box.set_margin_start(4)
        self.history_box.set_margin_end(4)
        scroll.add(self.history_box)
        self.scroll = scroll
        self.pack_start(scroll, True, True, 0)

        # Input row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.input_entry = Gtk.Entry()
        self.input_entry.set_placeholder_text('Ask Claude...')
        self.input_entry.connect('activate', self._send)
        send_btn = Gtk.Button(label='Send')
        send_btn.get_style_context().add_class('accent')
        send_btn.connect('clicked', self._send)
        clear_btn = Gtk.Button(label='Clear')
        clear_btn.connect('clicked', self._clear)
        input_row.pack_start(self.input_entry, True, True, 0)
        input_row.pack_start(send_btn, False, False, 0)
        input_row.pack_start(clear_btn, False, False, 0)
        self.pack_start(input_row, False, False, 4)

    def _add_message(self, role: str, text: str):
        """Add a message bubble to the history box. Must be called from GTK main thread."""
        lbl = Gtk.Label(label=text)
        lbl.set_line_wrap(True)
        lbl.set_xalign(1.0 if role == 'user' else 0.0)
        lbl.set_selectable(True)
        if role == 'user':
            lbl.get_style_context().add_class('chat-user')
        elif role == 'error':
            lbl.get_style_context().add_class('chat-error')
        else:
            lbl.get_style_context().add_class('chat-assistant')
        self.history_box.pack_start(lbl, False, False, 0)
        lbl.show()
        # Scroll to bottom
        adj = self.scroll.get_vadjustment()
        adj.set_value(adj.get_upper())

    def _send(self, _widget):
        text = self.input_entry.get_text().strip()
        if not text:
            return
        self.input_entry.set_text('')
        self.history.append({'role': 'user', 'content': text})
        self._add_message('user', text)
        self.error_label.hide()

        # Show a "..." placeholder while waiting
        waiting_lbl = Gtk.Label(label='...')
        waiting_lbl.get_style_context().add_class('chat-assistant')
        waiting_lbl.set_xalign(0.0)
        self.history_box.pack_start(waiting_lbl, False, False, 0)
        waiting_lbl.show()

        def do_request():
            try:
                client = anthropic.Anthropic(api_key=self.config.get('anthropic_api_key', ''))
                response = client.messages.create(
                    model=self.config.get('claude_model', 'claude-haiku-4-5-20251001'),
                    max_tokens=1024,
                    messages=self.history,
                )
                reply = response.content[0].text
                self.history.append({'role': 'assistant', 'content': reply})
                GLib.idle_add(self._on_reply, waiting_lbl, reply)
            except anthropic.AuthenticationError:
                GLib.idle_add(self._on_error, waiting_lbl, 'Invalid Anthropic API key.')
            except Exception as e:
                GLib.idle_add(self._on_error, waiting_lbl, f'Error: {e}')

        threading.Thread(target=do_request, daemon=True).start()

    def _on_reply(self, waiting_lbl, reply):
        self.history_box.remove(waiting_lbl)
        self._add_message('assistant', reply)

    def _on_error(self, waiting_lbl, msg):
        self.history_box.remove(waiting_lbl)
        self._add_message('error', msg)

    def _clear(self, _):
        self.history.clear()
        for child in self.history_box.get_children():
            self.history_box.remove(child)
