from api.client import ApiClient

class NotesApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_all(self) -> list:
        return self.client.get('/notes') or []

    def create(self, title: str, content: str = None) -> dict:
        return self.client.post('/notes', {'title': title, 'content': content})

    def update(self, note_id: int, **fields) -> dict:
        return self.client.put(f'/notes/{note_id}', fields)

    def delete(self, note_id: int) -> None:
        self.client.delete(f'/notes/{note_id}')
