# tests/test_api_notes.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import MagicMock
from api.notes import NotesApi

class TestNotesApi(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.api = NotesApi(self.client)

    def test_get_all(self):
        self.client.get.return_value = []
        self.api.get_all()
        self.client.get.assert_called_once_with('/notes')

    def test_create(self):
        self.api.create('My Note', content='Hello')
        self.client.post.assert_called_once_with('/notes', {'title': 'My Note', 'content': 'Hello'})

    def test_update(self):
        self.api.update(5, content='Updated')
        self.client.put.assert_called_once_with('/notes/5', {'content': 'Updated'})

    def test_delete(self):
        self.api.delete(5)
        self.client.delete.assert_called_once_with('/notes/5')

if __name__ == '__main__':
    unittest.main()
