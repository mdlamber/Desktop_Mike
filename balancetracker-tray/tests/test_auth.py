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

    def test_raises_value_error_when_id_token_is_none(self):
        mock_creds = MagicMock()
        mock_creds.id_token = None
        with patch('auth.Credentials', return_value=mock_creds), \
             patch('auth.Request'):
            with self.assertRaises(ValueError):
                auth.get_id_token(CONFIG)
        mock_creds.refresh.assert_called_once()

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

class TestRunOauthFlow(unittest.TestCase):
    def test_raises_runtime_error_when_refresh_token_is_none(self):
        mock_creds = MagicMock()
        mock_creds.refresh_token = None
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        with patch('auth.InstalledAppFlow') as mock_flow_cls:
            mock_flow_cls.from_client_config.return_value = mock_flow
            with self.assertRaises(RuntimeError):
                auth.run_oauth_flow(dict(CONFIG))
        mock_flow.run_local_server.assert_called_once()

if __name__ == '__main__':
    unittest.main()
