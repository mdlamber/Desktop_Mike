# BalanceTracker Tray — Google OAuth Design

**Date:** 2026-02-22
**Status:** Approved

---

## Overview

Replace manual bearer token entry in the tray app with a full Google OAuth2 loopback flow. Users log in once via their system browser; a refresh token is stored in config and used to auto-generate fresh ID tokens on every startup.

---

## Architecture

A new `auth.py` module owns all OAuth logic. The rest of the app calls `auth.get_id_token(config)` and receives a fresh JWT string — it has no knowledge of the OAuth details.

`ApiClient` changes from a static `bearer_token` string to a `token_getter` callable. On 401, it refreshes and retries once.

**New libraries:**
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`

---

## Config

`bearer_token` removed. New fields:

```json
{
  "client_id": "xxx.apps.googleusercontent.com",
  "client_secret": "GOCSPX-...",
  "refresh_token": "",
  "anthropic_api_key": "sk-ant-...",
  "claude_model": "claude-haiku-4-5-20251001",
  "backend_url": "http://localhost:3000"
}
```

After first login, `refresh_token` is populated and the OAuth flow never runs again.

---

## Auth Module (`auth.py`)

Two public functions:

**`ensure_authenticated(config) -> dict`**
- Called at startup
- If `refresh_token` present: validates credentials, returns updated config
- If `refresh_token` missing: runs the OAuth flow, stores refresh token, returns updated config

**`get_id_token(config) -> str`**
- Called per-request (via `ApiClient` token_getter)
- Refreshes credentials using stored refresh token
- Returns fresh ID token JWT string

**OAuth flow:**
1. Spin up temporary `http.server` on a random available port
2. Build Google auth URL with `offline` access type (ensures refresh token is issued)
3. Open URL via `webbrowser.open()`
4. Capture `?code=` callback, exchange for tokens via `google-auth-oauthlib`
5. Store `refresh_token` in config file

---

## Startup Sequence

1. Load config
2. If `client_id` or `client_secret` missing → show setup dialog
3. If `refresh_token` missing → run OAuth flow (open browser, capture callback)
4. If `anthropic_api_key` missing → show Anthropic key dialog
5. Build `ApiClient` with `token_getter=lambda: get_id_token(config)`
6. Launch tray window

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| OAuth flow cancelled | App exits with printed message |
| Refresh token revoked/expired | Inline "Session expired" banner with "Sign in again" button — re-runs OAuth flow without restart |
| Network down during token refresh | Surfaces as connection error (same as today) |
| 401 after token refresh | `PermissionError` raised, shown as inline error in panel |

---

## Prerequisites (one-time, user-managed)

Add `http://localhost` to **Authorized redirect URIs** in Google Cloud Console for the OAuth client. The `install.sh` script prints a reminder.

---

## Files Changed

| File | Change |
|---|---|
| `auth.py` | New — OAuth flow and token refresh |
| `config.py` | Remove `bearer_token` default, add `client_id`, `client_secret`, `refresh_token` |
| `api/client.py` | Accept `token_getter` callable; retry on 401 |
| `app.py` | Call `ensure_authenticated`, pass `token_getter` to window/clients; update setup dialog |
| `requirements.txt` | Add `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2` |
| `install.sh` | Print Google Console redirect URI reminder |
