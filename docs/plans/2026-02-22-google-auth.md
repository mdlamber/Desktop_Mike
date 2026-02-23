# Google OAuth Loopback Flow — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace manual bearer token entry in the tray app with a Google OAuth2 loopback flow that stores a refresh token and auto-generates fresh ID tokens on every API call.

**Architecture:** New `auth.py` module owns all OAuth logic. `ApiClient` changes from a static `bearer_token` string to a `token_getter` callable and retries once on 401. `TrayWindow` accepts `token_getter` from `app.py`. On startup, `app.py` calls `ensure_authenticated(config)` to run the OAuth flow if no refresh token is stored.

**Tech Stack:** `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, Python unittest/mock, GTK3

---

### Task 1: Update config.py — remove bearer_token, add OAuth fields

**Files:**
- Modify: `config.py`
- Modify: `tests/test_config.py`

**Step 1: Update tests/test_config.py first**

Replace `tests/test_config.py` entirely:

```python
import json, os, tempfile, unittest, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config as cfg

class TestConfig(unittest.TestCase):
    def test_load_valid_config(self):
        data = {'client_id': 'cid', 'client_secret': 'cs', 'anthropic_api_key': 'sk-ant-xxx'}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = cfg.load_config(path)
            self.assertEqual(result['client_id'], 'cid')
            self.assertEqual(result['client_secret'], 'cs')
            self.assertEqual(result['anthropic_api_key'], 'sk-ant-xxx')
            self.assertEqual(result['claude_model'], 'claude-haiku-4-5-20251001')
        finally:
            os.unlink(path)

    def test_missing_file_returns_defaults(self):
        result = cfg.load_config('/nonexistent/path/config.json')
        self.assertNotIn('bearer_token', result)
        self.assertEqual(result['client_id'], '')
        self.assertEqual(result['client_secret'], '')
        self.assertEqual(result['refresh_token'], '')
        self.assertEqual(result['anthropic_api_key'], '')

    def test_save_and_reload_roundtrip(self):
        data = {'client_id': 'cid', 'refresh_token': 'rt', 'anthropic_api_key': 'key'}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'sub', 'config.json')
            cfg.save_config(data, path)
            loaded = cfg.load_config(path)
            self.assertEqual(loaded['client_id'], 'cid')
            self.assertEqual(loaded['refresh_token'], 'rt')

if __name__ == '__main__':
    unittest.main()
```

**Step 2: Run tests, confirm they fail**

Run: `python3 -m unittest tests/test_config.py -v`
Expected: FAIL — `test_missing_file_returns_defaults` fails because `bearer_token` key exists and `client_id` doesn't

**Step 3: Update config.py DEFAULTS**

In `config.py`, replace the `DEFAULTS` dict:

```python
DEFAULTS = {
    'client_id': '',
    'client_secret': '',
    'refresh_token': '',
    'anthropic_api_key': '',
    'claude_model': 'claude-haiku-4-5-20251001',
    'backend_url': 'http://localhost:3000',
}
```

**Step 4: Run tests, confirm they pass**

Run: `python3 -m unittest tests/test_config.py -v`
Expected: OK (3 tests)

**Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: replace bearer_token with Google OAuth fields in config"
```

---

### Task 2: Create auth.py — OAuth loopback flow and token refresh

**Files:**
- Create: `auth.py`
- Create: `tests/test_auth.py`

**Step 1: Install new Python dependencies**

Run: `pip install google-auth google-auth-oauthlib google-auth-httplib2`
Expected: Successfully installed (or already satisfied)

**Step 2: Write the failing tests**

Create `tests/test_auth.py`:

```python
import sys, os, unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import auth

CONFIG = {
    'client_id': 'test-client-id.apps.googleusercontent.com',
    'client_secret': 'GOCSPX-testsecret',
    'refresh_token': 'test-refresh-token',
    'backend_url': 'http://localhost:3000',
}

class TestGetIdToken(unittest.TestCase):
    def test_returns_id_token_from_credentials(self):
        mock_creds = MagicMock()
        mock_creds.id_token = 'eyJfakeIdToken'
        with patch('auth.Credentials', return_value=mock_creds), \
             patch('auth.Request'):
            result = auth.get_id_token(CONFIG)
            mock_creds.refresh.assert_called_once()
            self.assertEqual(result, 'eyJfakeIdToken')

class TestEnsureAuthenticated(unittest.TestCase):
    def test_skips_flow_when_refresh_token_present(self):
        with patch('auth.run_oauth_flow') as mock_flow:
            result = auth.ensure_authenticated(dict(CONFIG))
            mock_flow.assert_not_called()
            self.assertEqual(result['refresh_token'], 'test-refresh-token')

    def test_runs_flow_when_refresh_token_missing(self):
        config = {**CONFIG, 'refresh_token': ''}
        updated = {**config, 'refresh_token': 'brand-new-token'}
        with patch('auth.run_oauth_flow', return_value=updated) as mock_flow:
            result = auth.ensure_authenticated(config)
            mock_flow.assert_called_once_with(config)
            self.assertEqual(result['refresh_token'], 'brand-new-token')

if __name__ == '__main__':
    unittest.main()
```

**Step 3: Run tests, confirm they fail**

Run: `python3 -m unittest tests/test_auth.py -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'auth'`

**Step 4: Create auth.py**

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['openid', 'email', 'profile']
TOKEN_URI = 'https://oauth2.googleapis.com/token'


def get_id_token(config: dict) -> str:
    creds = Credentials(
        token=None,
        refresh_token=config['refresh_token'],
        token_uri=TOKEN_URI,
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds.id_token


def run_oauth_flow(config: dict) -> dict:
    client_config = {
        'installed': {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': TOKEN_URI,
            'redirect_uris': ['http://localhost'],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    config['refresh_token'] = creds.refresh_token
    return config


def ensure_authenticated(config: dict) -> dict:
    if not config.get('refresh_token'):
        config = run_oauth_flow(config)
    return config
```

**Step 5: Run tests, confirm they pass**

Run: `python3 -m unittest tests/test_auth.py -v`
Expected: OK (3 tests)

**Step 6: Run all tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: OK (all tests pass)

**Step 7: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: add auth module with Google OAuth loopback flow"
```

---

### Task 3: Update api/client.py — token_getter callable, retry once on 401

**Files:**
- Modify: `api/client.py`
- Modify: `tests/test_api_client.py`

**Step 1: Update tests/test_api_client.py**

Replace `tests/test_api_client.py` entirely:

```python
import sys, os, unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from api.client import ApiClient

def make_client(token='test-token'):
    return ApiClient(base_url='http://localhost:3000', token_getter=lambda: token)

class TestApiClient(unittest.TestCase):
    def test_get_injects_auth_header(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.content = b'[]'
        with patch('requests.get', return_value=mock_resp) as mock_get:
            result = make_client().get('/tasks')
            headers = mock_get.call_args[1]['headers']
            self.assertEqual(headers['Authorization'], 'Bearer test-token')
            self.assertEqual(result, [])

    def test_post_sends_json_body(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {'id': 1}
        mock_resp.content = b'{"id": 1}'
        with patch('requests.post', return_value=mock_resp) as mock_post:
            result = make_client().post('/tasks', {'subject': 'Test'})
            self.assertEqual(mock_post.call_args[1]['json'], {'subject': 'Test'})
            self.assertEqual(result, {'id': 1})

    def test_401_retries_and_succeeds(self):
        fail_resp = MagicMock()
        fail_resp.status_code = 401
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = []
        ok_resp.content = b'[]'
        tokens = iter(['old-token', 'fresh-token'])
        client = ApiClient('http://localhost:3000', token_getter=lambda: next(tokens))
        with patch('requests.get', side_effect=[fail_resp, ok_resp]) as mock_get:
            result = client.get('/tasks')
            self.assertEqual(mock_get.call_count, 2)
            self.assertEqual(result, [])

    def test_401_twice_raises_permission_error(self):
        fail_resp = MagicMock()
        fail_resp.status_code = 401
        with patch('requests.get', return_value=fail_resp):
            with self.assertRaises(PermissionError):
                make_client().get('/tasks')

    def test_network_error_raises_connection_error(self):
        import requests
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError()):
            with self.assertRaises(ConnectionError):
                make_client().get('/tasks')

if __name__ == '__main__':
    unittest.main()
```

**Step 2: Run tests, confirm they fail**

Run: `python3 -m unittest tests/test_api_client.py -v`
Expected: FAIL — `TypeError` because `ApiClient.__init__` still has `bearer_token` parameter

**Step 3: Rewrite api/client.py**

```python
import requests


class ApiClient:
    def __init__(self, base_url: str, token_getter):
        self.base_url = base_url.rstrip('/')
        self.token_getter = token_getter

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.token_getter()}',
            'Content-Type': 'application/json',
        }

    def _request(self, method, path, **kwargs):
        url = f'{self.base_url}{path}'
        try:
            resp = method(url, headers=self._headers(), timeout=10, **kwargs)
            if resp.status_code == 401:
                resp = method(url, headers=self._headers(), timeout=10, **kwargs)
                if resp.status_code == 401:
                    raise PermissionError('Authentication failed after token refresh.')
            resp.raise_for_status()
            return resp.json() if resp.content else None
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend at {self.base_url}: {e}')

    def get(self, path: str):
        return self._request(requests.get, path)

    def post(self, path: str, body: dict):
        return self._request(requests.post, path, json=body)

    def put(self, path: str, body: dict):
        return self._request(requests.put, path, json=body)

    def delete(self, path: str):
        return self._request(requests.delete, path)
```

**Step 4: Run tests, confirm they pass**

Run: `python3 -m unittest tests/test_api_client.py -v`
Expected: OK (5 tests)

**Step 5: Run all tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: OK (all tests)

**Step 6: Commit**

```bash
git add api/client.py tests/test_api_client.py
git commit -m "feat: ApiClient accepts token_getter callable, retries on 401"
```

---

### Task 4: Update window.py and app.py — wire token_getter through the stack

**Files:**
- Modify: `window.py`
- Modify: `app.py`

No unit tests for GTK UI code. Verification is syntax check + full test run.

**Step 1: Update window.py**

In `window.py`, change `__init__` to accept `token_getter` and update `_setup_api`:

Change `def __init__(self):` to `def __init__(self, token_getter):` and add `self.token_getter = token_getter` as the first line of the body, before calling `self._setup_window()`.

Change `_setup_api` to:

```python
def _setup_api(self):
    client = ApiClient(
        base_url=self.config.get('backend_url', 'http://localhost:3000'),
        token_getter=self.token_getter,
    )
    self.tasks_api = TasksApi(client)
    self.notes_api = NotesApi(client)
```

**Step 2: Rewrite app.py**

```python
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
```

**Step 3: Verify syntax**

Run: `python3 -m py_compile window.py app.py && echo OK`
Expected: `OK`

**Step 4: Run all tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: OK (all tests — 3 config + 3 auth + 5 client + 4 tasks + 4 notes = 19 total)

**Step 5: Commit**

```bash
git add window.py app.py
git commit -m "feat: wire token_getter through TrayWindow and app startup"
```

---

### Task 5: Update requirements.txt and install.sh

**Files:**
- Modify: `requirements.txt`
- Modify: `install.sh`

**Step 1: Replace requirements.txt**

```
PyGObject>=3.42.0
requests>=2.28.0
anthropic>=0.25.0
google-auth>=2.28.0
google-auth-oauthlib>=1.2.0
google-auth-httplib2>=0.2.0
```

**Step 2: Read install.sh and add redirect URI reminder**

Read `install.sh` to find the end of the file. After the final AppIndicator extension check block, append:

```bash
echo ""
echo "IMPORTANT: Before first run, add http://localhost to your OAuth client's"
echo "Authorized redirect URIs at:"
echo "  https://console.cloud.google.com/apis/credentials"
echo ""
echo "On first launch a browser window will open for Google sign-in."
echo "After you sign in, the tray app starts automatically."
```

**Step 3: Verify install.sh syntax**

Run: `bash -n install.sh && echo OK`
Expected: `OK`

**Step 4: Run all tests one final time**

Run: `python3 -m unittest discover -s tests -v`
Expected: OK (19 tests)

**Step 5: Commit**

```bash
git add requirements.txt install.sh
git commit -m "feat: add Google auth dependencies, update install guidance"
```
