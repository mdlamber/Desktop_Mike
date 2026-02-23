# tests/test_api_tasks.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import MagicMock
from api.tasks import TasksApi

class TestTasksApi(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.api = TasksApi(self.client)

    def test_get_all_calls_get(self):
        self.client.get.return_value = [{'id': 1, 'subject': 'Do thing'}]
        result = self.api.get_all()
        self.client.get.assert_called_once_with('/tasks')
        self.assertEqual(len(result), 1)

    def test_create_calls_post(self):
        self.client.post.return_value = {'id': 2, 'subject': 'New task'}
        result = self.api.create('New task', description='desc', notes=None, status='todo')
        self.client.post.assert_called_once_with('/tasks', {
            'subject': 'New task', 'description': 'desc', 'notes': None, 'status': 'todo'
        })

    def test_update_calls_put(self):
        self.client.put.return_value = {'id': 1, 'status': 'done'}
        self.api.update(1, status='done')
        self.client.put.assert_called_once_with('/tasks/1', {'status': 'done'})

    def test_delete_calls_delete(self):
        self.api.delete(3)
        self.client.delete.assert_called_once_with('/tasks/3')

if __name__ == '__main__':
    unittest.main()
