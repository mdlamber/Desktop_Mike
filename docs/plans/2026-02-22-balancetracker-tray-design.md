# BalanceTracker Tray App — Design Document

**Date:** 2026-02-22
**Status:** Approved

---

## Overview

A Linux desktop tray application for Fedora GNOME that connects to the existing BalanceTracker NestJS backend. Lives in the GNOME top bar via AppIndicator protocol, provides a compact translucent popup window for managing tasks, notes, and a Claude AI chat interface.

---

## Tech Stack

- **Language:** Python 3
- **UI toolkit:** GTK3 (PyGObject / gi.repository)
- **Tray protocol:** libayatana-appindicator3
- **HTTP client:** `requests`
- **AI client:** `anthropic` Python library
- **Service management:** systemd user service
- **Backend:** Existing BalanceTracker NestJS API (localhost:3000)

---

## Architecture

### Two parts:

**1. Backend changes (BalanceTracker)**
- Extend `Task` entity: add `subject` (text, required) + `status` (enum: `todo | in_progress | done`, default `todo`)
- New `Note` entity: `id`, `title`, `content`, `createdAt`, `updatedAt`
- New `notes/` NestJS module: `GET /notes`, `POST /notes`, `PUT /notes/:id`, `DELETE /notes/:id` — all protected by `GoogleTokenGuard`
- TypeORM migration for both schema changes

**2. Tray App** — `~/Projects/Desktop_Mike/balancetracker-tray/`
- AppIndicator3 icon in GNOME top bar
- Single GTK3 window toggled by tray icon click or Escape key
- Window: 480×600px (~1/8 of 1920×1080), semi-transparent (`rgba(10,10,10,0.88)`)
- Three tabs: Tasks | Notes | Chat

---

## File Structure

```
balancetracker-tray/
├── app.py                       — entry point: AppIndicator, window toggle
├── window.py                    — GTK3 Window, Notebook tabs container
├── config.py                    — load/save ~/.config/balancetracker-tray/config.json
├── api/
│   ├── client.py                — base HTTP client (Bearer token injection, error handling)
│   ├── tasks.py                 — CRUD wrappers for /tasks
│   └── notes.py                 — CRUD wrappers for /notes
├── panels/
│   ├── tasks.py                 — Tasks panel widget
│   ├── notes.py                 — Notes panel widget
│   └── chat.py                  — Claude chat panel widget
├── assets/
│   └── icon.png                 — tray icon
├── style.css                    — GTK3 CSS: dark theme, rgba translucency, green accents
├── balancetracker-tray.service  — systemd user unit file
├── requirements.txt
└── install.sh                   — venv setup, dep install, systemd enable
```

**Backend additions:**
```
server/src/
├── entities/
│   ├── task.entity.ts           — add subject + status columns
│   └── note.entity.ts           — new entity
├── notes/
│   ├── notes.controller.ts
│   ├── notes.service.ts
│   └── notes.module.ts
└── migrations/
    └── <timestamp>-AddSubjectStatusAndNotes.ts
```

---

## UI Panels

### Window Behavior
- Fixed size: 480×600px, positioned near top-right (tray area)
- `set_app_paintable(True)` + RGBA visual for compositor-backed translucency
- No window decorations, rounded corners via CSS
- Toggle: tray icon click or Escape; clicking outside does NOT close it

### Tasks Panel
- Scrollable list: each row shows `[STATUS BADGE] subject`
- Click row to expand: shows `description`, `notes`, Edit/Delete buttons
- "+" button opens inline creation form: subject (required), description, notes, status dropdown
- Status badge colors: `todo` = grey, `in_progress` = yellow, `done` = green

### Notes Panel
- Two-pane: left = scrollable note titles list; right = editable content text area
- "+" creates new note (inline title prompt); trash deletes selected note
- Auto-saves to `PUT /notes/:id` after 1.5s debounce on keystroke

### Chat Panel
- Scrollable history: user messages right-aligned (green), Claude left-aligned (white/grey)
- Text entry + Send button; Enter key sends
- Model: `claude-haiku-4-5-20251001` (fast, configurable via config.json)
- Conversation resets on app restart (in-memory only)
- Async API calls via `threading.Thread` + `GLib.idle_add` for UI safety

---

## Styling

- Background: `rgba(10, 10, 10, 0.88)` — near-black, translucent
- Accent / primary text: `#00C853` (bright green)
- Secondary text: `#cccccc`
- Font: `Monospace 9`
- Tab bar, borders, inputs all use dark/green palette

---

## Config

File: `~/.config/balancetracker-tray/config.json`

```json
{
  "bearer_token": "<google_id_token>",
  "anthropic_api_key": "sk-ant-...",
  "claude_model": "claude-haiku-4-5-20251001"
}
```

If missing on startup, app shows a setup dialog to enter credentials.

---

## Auth & Data Flow

- All backend requests inject `Authorization: Bearer <token>` via `api/client.py`
- 401 response → inline error banner: "Token expired — update config.json and restart"
- Tasks: full list re-fetched after every create/update/delete (no local cache)
- Notes: list fetched on panel show; content fetched on selection; debounced auto-save on edit
- Chat: calls Anthropic API directly (never proxied through backend)

---

## Error Handling

- Network errors → non-blocking inline error label in affected panel
- Anthropic errors → error message shown inline in chat history
- App does not crash on any API failure
- All API calls on background threads; UI updates via `GLib.idle_add`

---

## systemd User Service

File: `~/.config/systemd/user/balancetracker-tray.service`

```ini
[Unit]
Description=BalanceTracker Tray App

[Service]
ExecStart=/home/<user>/Projects/Desktop_Mike/balancetracker-tray/.venv/bin/python app.py
WorkingDirectory=/home/<user>/Projects/Desktop_Mike/balancetracker-tray
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
```

---

## Prerequisites (one-time setup)

1. Install `gnome-shell-extension-appindicator`:
   ```bash
   sudo dnf install gnome-shell-extension-appindicator
   gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
   ```
2. Install system dependencies:
   ```bash
   sudo dnf install python3-gobject python3-gobject-devel libayatana-appindicator-gtk3
   ```
3. Run `install.sh` to set up the venv and enable the systemd service
