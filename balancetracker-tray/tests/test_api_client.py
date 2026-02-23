# tests/test_api_client.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import patch, MagicMock
from api.client import ApiClient

class TestApiClient(unittest.TestCase):

    def setUp(self):
        self.client = ApiClient(base_url='http://localhost:3000', bearer_token='test-token')

    def test_get_injects_auth_header(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.content = b'[]'
        with patch('requests.get', return_value=mock_resp) as mock_get:
            result = self.client.get('/tasks')
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args
            self.assertEqual(call_kwargs[1]['headers']['Authorization'], 'Bearer test-token')
            self.assertEqual(result, [])

    def test_post_sends_json_body(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {'id': 1}
        mock_resp.content = b'{"id": 1}'
        with patch('requests.post', return_value=mock_resp) as mock_post:
            result = self.client.post('/tasks', {'subject': 'Test'})
            call_kwargs = mock_post.call_args
            self.assertEqual(call_kwargs[1]['json'], {'subject': 'Test'})
            self.assertEqual(result, {'id': 1})

    def test_401_raises_auth_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = Exception('401')
        with patch('requests.get', return_value=mock_resp):
            with self.assertRaises(PermissionError):
                self.client.get('/tasks')

    def test_network_error_raises_connection_error(self):
        import requests
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError()):
            with self.assertRaises(ConnectionError):
                self.client.get('/tasks')

if __name__ == '__main__':
    unittest.main()
