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
