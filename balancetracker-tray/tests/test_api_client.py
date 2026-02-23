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
