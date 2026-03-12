# BalanceTracker Tray

A Linux system tray app for managing tasks and notes via the BalanceTracker backend. Runs as a GNOME panel widget with a dark, translucent popup window.

## Prerequisites

- Fedora with GNOME desktop
- Python 3
- System packages:
  ```
  sudo dnf install python3-gobject libayatana-appindicator-gtk3 gnome-shell-extension-appindicator
  ```
- Google OAuth client credentials (client ID + secret) from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
  - Add `http://localhost` to **Authorized redirect URIs**

## Install

```bash
./install.sh
```

This creates a Python venv, installs dependencies, and sets up a systemd user service that starts on login.

On first launch, a browser window opens for Google sign-in. After authenticating, the tray icon appears and the app runs automatically.

## Usage

```bash
# Start
systemctl --user start balancetracker-tray

# Stop
systemctl --user stop balancetracker-tray

# Restart (after code changes)
systemctl --user restart balancetracker-tray

# View logs
journalctl --user -u balancetracker-tray -f

# Check status
systemctl --user status balancetracker-tray
```

Click the tray icon to toggle the panel. Press **Escape** to hide it.

## Autostart

The install script enables the service to start on login. To manage this manually:

```bash
# Enable autostart
systemctl --user enable balancetracker-tray

# Disable autostart
systemctl --user disable balancetracker-tray
```

## Running Tests

```bash
.venv/bin/python3 -m unittest discover tests
```

## Config

Stored at `~/.config/balancetracker-tray/config.json`:

| Key | Description |
|-----|-------------|
| `client_id` | Google OAuth client ID |
| `client_secret` | Google OAuth client secret |
| `refresh_token` | Stored after first sign-in |
| `backend_url` | Backend API URL (default: `http://localhost:3000`) |
