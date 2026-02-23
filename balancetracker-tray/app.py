#!/usr/bin/env python3
import os
import sys
import signal
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AppIndicator3

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

    if not config.get('anthropic_api_key'):
        _show_anthropic_dialog(config)

    try:
        config = ensure_authenticated(config)
        save_config(config)
    except Exception as e:
        print(f'Authentication failed: {e}')
        sys.exit(1)

    token_getter = lambda: get_id_token(config)
    window = TrayWindow(token_getter=token_getter)
    window.hide()

    indicator = AppIndicator3.Indicator.new(
        'balancetracker-tray',
        ICON_PATH,
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    indicator.set_title('BalanceTracker')

    menu = Gtk.Menu()

    def on_menu_show(m):
        m.hide()
        GLib.idle_add(window.toggle)

    menu.connect('show', on_menu_show)

    item = Gtk.MenuItem(label='BalanceTracker')
    item.connect('activate', lambda _: window.toggle())
    menu.append(item)

    menu.append(Gtk.SeparatorMenuItem())
    quit_item = Gtk.MenuItem(label='Quit')
    quit_item.connect('activate', lambda _: Gtk.main_quit())
    menu.append(quit_item)

    menu.show_all()
    indicator.set_menu(menu)

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


def _show_anthropic_dialog(config: dict):
    dialog = Gtk.Dialog(title='BalanceTracker — Anthropic API Key')
    dialog.add_buttons('Save', Gtk.ResponseType.OK, 'Skip', Gtk.ResponseType.CANCEL)
    box = dialog.get_content_area()

    key_entry = Gtk.Entry()
    key_entry.set_placeholder_text('sk-ant-...')
    key_entry.set_text(config.get('anthropic_api_key', ''))
    key_entry.set_width_chars(60)
    key_entry.set_visibility(False)

    box.pack_start(Gtk.Label(label='Anthropic API Key (required for Chat tab):'), False, False, 4)
    box.pack_start(key_entry, False, False, 4)
    dialog.show_all()

    if dialog.run() == Gtk.ResponseType.OK:
        config['anthropic_api_key'] = key_entry.get_text().strip()
        save_config(config)
    dialog.destroy()


if __name__ == '__main__':
    main()
