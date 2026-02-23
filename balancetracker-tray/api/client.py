import requests

class ApiClient:
    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url.rstrip('/')
        self.bearer_token = bearer_token

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
        }

    def _handle_response(self, resp: requests.Response):
        if resp.status_code == 401:
            raise PermissionError('Bearer token rejected (401). Update config.json and restart.')
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return None

    def get(self, path: str):
        try:
            resp = requests.get(f'{self.base_url}{path}', headers=self._headers(), timeout=10)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend at {self.base_url}: {e}')

    def post(self, path: str, body: dict):
        try:
            resp = requests.post(f'{self.base_url}{path}', headers=self._headers(), json=body, timeout=10)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend: {e}')

    def put(self, path: str, body: dict):
        try:
            resp = requests.put(f'{self.base_url}{path}', headers=self._headers(), json=body, timeout=10)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend: {e}')

    def delete(self, path: str):
        try:
            resp = requests.delete(f'{self.base_url}{path}', headers=self._headers(), timeout=10)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend: {e}')
