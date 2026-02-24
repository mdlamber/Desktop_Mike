#!/usr/bin/env python3
import os
import sys
import signal
import warnings
warnings.filterwarnings('ignore', message='.*StatusIcon.*deprecated.*')
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

from window import TrayWindow
from config import load_config, save_config
from auth import ensure_authenticated, get_id_token

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
ICON_PATH = os.path.join(ASSETS_DIR, 'icon.png')


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    config = load_config()

    if not config.get('client_id') or not config.get('client_secret'):
        _show_credentials_dialog(config)
        if not config.get('client_id') or not config.get('client_secret'):
            print('Google OAuth credentials required. Exiting.')
            sys.exit(1)

    try:
        config = ensure_authenticated(config)
        save_config(config)
    except Exception as e:
        print(f'Authentication failed: {e}')
        sys.exit(1)

    token_getter = lambda: get_id_token(config)
    window = TrayWindow(token_getter=token_getter)

    icon = Gtk.StatusIcon()
    icon.set_from_file(ICON_PATH)
    icon.set_tooltip_text('BalanceTracker')
    icon.set_visible(True)
    icon.connect('activate', lambda _: window.toggle())

    Gtk.main()


def _show_credentials_dialog(config: dict):
    dialog = Gtk.Dialog(title='BalanceTracker — Google OAuth Setup')
    dialog.add_buttons('Save', Gtk.ResponseType.OK, 'Cancel', Gtk.ResponseType.CANCEL)
    box = dialog.get_content_area()

    box.pack_start(
        Gtk.Label(label='Find these at: Google Cloud Console → APIs & Services → Credentials'),
        False, False, 8,
    )

    client_id_entry = Gtk.Entry()
    client_id_entry.set_placeholder_text('Client ID  (xxx.apps.googleusercontent.com)')
    client_id_entry.set_text(config.get('client_id', ''))
    client_id_entry.set_width_chars(60)

    client_secret_entry = Gtk.Entry()
    client_secret_entry.set_placeholder_text('Client Secret  (GOCSPX-...)')
    client_secret_entry.set_text(config.get('client_secret', ''))
    client_secret_entry.set_width_chars(60)
    client_secret_entry.set_visibility(False)

    box.pack_start(Gtk.Label(label='Client ID:'), False, False, 4)
    box.pack_start(client_id_entry, False, False, 4)
    box.pack_start(Gtk.Label(label='Client Secret:'), False, False, 4)
    box.pack_start(client_secret_entry, False, False, 4)
    dialog.show_all()

    if dialog.run() == Gtk.ResponseType.OK:
        config['client_id'] = client_id_entry.get_text().strip()
        config['client_secret'] = client_secret_entry.get_text().strip()
        save_config(config)
    dialog.destroy()


if __name__ == '__main__':
    main()
