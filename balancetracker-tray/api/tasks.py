from api.client import ApiClient

class TasksApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_all(self) -> list:
        return self.client.get('/tasks') or []

    def create(self, subject: str, description: str = None, notes: str = None, status: str = 'todo') -> dict:
        return self.client.post('/tasks', {
            'subject': subject,
            'description': description,
            'notes': notes,
            'status': status,
        })

    def update(self, task_id: int, **fields) -> dict:
        return self.client.put(f'/tasks/{task_id}', fields)

    def delete(self, task_id: int) -> None:
        self.client.delete(f'/tasks/{task_id}')
