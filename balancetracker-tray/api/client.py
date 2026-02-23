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
