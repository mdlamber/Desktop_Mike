#!/usr/bin/env python3
# app.py — BalanceTracker Tray App entry point
import os
import sys
import signal
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AppIndicator3

from window import TrayWindow
from config import load_config, save_config, CONFIG_PATH

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
ICON_PATH = os.path.join(ASSETS_DIR, 'icon.png')

def main():
    # Allow Ctrl+C to terminate cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Ensure config exists; prompt user if not
    config = load_config()
    if not config.get('bearer_token') or not config.get('anthropic_api_key'):
        _show_setup_dialog(config)

    # Create the main window (hidden initially)
    window = TrayWindow()
    window.hide()

    # Create the AppIndicator
    indicator = AppIndicator3.Indicator.new(
        'balancetracker-tray',
        ICON_PATH,
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    indicator.set_title('BalanceTracker')

    # Build a minimal menu that immediately toggles the window and hides itself
    menu = Gtk.Menu()

    def on_menu_show(m):
        m.hide()
        GLib.idle_add(window.toggle)

    menu.connect('show', on_menu_show)

    # Fallback item (never visible normally, but menu must be non-empty)
    item = Gtk.MenuItem(label='BalanceTracker')
    item.connect('activate', lambda _: window.toggle())
    menu.append(item)

    quit_item = Gtk.SeparatorMenuItem()
    menu.append(quit_item)
    quit_item2 = Gtk.MenuItem(label='Quit')
    quit_item2.connect('activate', lambda _: Gtk.main_quit())
    menu.append(quit_item2)

    menu.show_all()
    indicator.set_menu(menu)

    Gtk.main()


def _show_setup_dialog(config: dict):
    dialog = Gtk.Dialog(title='BalanceTracker Tray — Setup')
    dialog.add_buttons('Save', Gtk.ResponseType.OK, 'Skip', Gtk.ResponseType.CANCEL)
    box = dialog.get_content_area()

    token_entry = Gtk.Entry()
    token_entry.set_placeholder_text('Google ID Token (Bearer)')
    token_entry.set_text(config.get('bearer_token', ''))
    token_entry.set_width_chars(50)

    api_key_entry = Gtk.Entry()
    api_key_entry.set_placeholder_text('Anthropic API Key (sk-ant-...)')
    api_key_entry.set_text(config.get('anthropic_api_key', ''))
    api_key_entry.set_width_chars(50)

    box.pack_start(Gtk.Label(label='Bearer Token:'), False, False, 4)
    box.pack_start(token_entry, False, False, 4)
    box.pack_start(Gtk.Label(label='Anthropic API Key:'), False, False, 4)
    box.pack_start(api_key_entry, False, False, 4)
    dialog.show_all()

    if dialog.run() == Gtk.ResponseType.OK:
        config['bearer_token'] = token_entry.get_text().strip()
        config['anthropic_api_key'] = api_key_entry.get_text().strip()
        save_config(config)
    dialog.destroy()


if __name__ == '__main__':
    main()
