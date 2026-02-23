# tests/test_config.py
import json
import os
import tempfile
import unittest
from unittest.mock import patch

# Add parent to path so we can import config
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config as cfg

class TestConfig(unittest.TestCase):

    def test_load_valid_config(self):
        data = {"bearer_token": "tok123", "anthropic_api_key": "sk-ant-xxx"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = cfg.load_config(path)
            self.assertEqual(result['bearer_token'], 'tok123')
            self.assertEqual(result['anthropic_api_key'], 'sk-ant-xxx')
            self.assertEqual(result.get('claude_model'), 'claude-haiku-4-5-20251001')
        finally:
            os.unlink(path)

    def test_missing_file_returns_defaults(self):
        result = cfg.load_config('/nonexistent/path/config.json')
        self.assertEqual(result['bearer_token'], '')
        self.assertEqual(result['anthropic_api_key'], '')

    def test_save_config(self):
        data = {"bearer_token": "tok", "anthropic_api_key": "key"}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'subdir', 'config.json')
            cfg.save_config(data, path)
            self.assertTrue(os.path.exists(path))
            loaded = json.loads(open(path).read())
            self.assertEqual(loaded['bearer_token'], 'tok')

if __name__ == '__main__':
    unittest.main()
