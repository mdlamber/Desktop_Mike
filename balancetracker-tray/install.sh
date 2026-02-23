#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="balancetracker-tray.service"

echo "==> Installing BalanceTracker Tray App"
echo ""

# 1. Check system dependencies
echo "--- Checking system dependencies ---"
MISSING=()
python3 -c "import gi" 2>/dev/null || MISSING+=("python3-gobject")
pkg-config --exists ayatana-appindicator3-0.1 2>/dev/null || \
  pkg-config --exists appindicator3-0.1 2>/dev/null || MISSING+=("libayatana-appindicator-gtk3")

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "Missing system packages: ${MISSING[*]}"
  echo "Run: sudo dnf install ${MISSING[*]}"
  exit 1
fi
echo "System dependencies OK."

# 2. Create Python venv
echo ""
echo "--- Creating Python virtual environment ---"
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$SCRIPT_DIR/.venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "venv ready at $SCRIPT_DIR/.venv"

# 3. Install systemd user service
echo ""
echo "--- Installing systemd user service ---"
mkdir -p "$SERVICE_DIR"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
sed \
  -e "s|VENV_PYTHON_PLACEHOLDER|$VENV_PYTHON|g" \
  -e "s|APP_DIR_PLACEHOLDER|$SCRIPT_DIR|g" \
  "$SCRIPT_DIR/balancetracker-tray.service" > "$SERVICE_DIR/$SERVICE_NAME"

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"
echo "Service enabled and started."

# 4. Check for AppIndicator GNOME extension
echo ""
echo "--- Checking GNOME AppIndicator extension ---"
if gnome-extensions list 2>/dev/null | grep -q "appindicatorsupport"; then
  gnome-extensions enable "appindicatorsupport@rgcjonas.gmail.com" 2>/dev/null || true
  echo "AppIndicator extension enabled."
else
  echo "NOTICE: gnome-shell-extension-appindicator not found."
  echo "Install it with:"
  echo "  sudo dnf install gnome-shell-extension-appindicator"
  echo "  gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com"
  echo "  (then log out and back in)"
fi

echo ""
echo "Done! The tray app is now running."
echo "Config file: $HOME/.config/balancetracker-tray/config.json"
echo ""
echo "To check status:  systemctl --user status balancetracker-tray"
echo "To view logs:     journalctl --user -u balancetracker-tray -f"
echo "To restart:       systemctl --user restart balancetracker-tray"
