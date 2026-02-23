# BalanceTracker Tray App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a GNOME AppIndicator tray app with Tasks/Notes/Chat panels backed by the BalanceTracker API, running as a systemd user service.

**Architecture:** Python + GTK3 + libayatana-appindicator3 for the tray UI. The NestJS backend is extended with `subject`/`status` on Task and a new Note entity. The popup window is translucent, sized at 1/8 of screen area, and toggles on tray-icon click. Config lives at `~/.config/balancetracker-tray/config.json`.

**Tech Stack:** Python 3, PyGObject (GTK3), libayatana-appindicator3, cairo, requests, anthropic, NestJS/TypeORM (SQLite, synchronize:true)

---

## Phase 1 — Backend Changes

### Task 1: Extend Task entity and service

**Files:**
- Modify: `~/Projects/BalanceTracker/server/src/entities/task.entity.ts`
- Modify: `~/Projects/BalanceTracker/server/src/tasks/tasks.service.ts`
- Modify: `~/Projects/BalanceTracker/server/src/tasks/tasks.controller.ts`

**Step 1: Update task.entity.ts**

Replace the entire file content with:

```typescript
import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';

export type TaskStatus = 'todo' | 'in_progress' | 'done';

@Entity('task')
export class Task {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'text' })
  subject: string;

  @Column({ type: 'text', nullable: true })
  description: string | null;

  @Column({ type: 'text', nullable: true })
  notes: string | null;

  @Column({ type: 'text', default: 'todo' })
  status: TaskStatus;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
```

**Step 2: Update tasks.service.ts**

Replace the entire file content with:

```typescript
import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Task, TaskStatus } from '../entities/task.entity.js';

interface CreateTaskDto {
  subject: string;
  description?: string | null;
  notes?: string | null;
  status?: TaskStatus;
}

interface UpdateTaskDto {
  subject?: string;
  description?: string | null;
  notes?: string | null;
  status?: TaskStatus;
}

@Injectable()
export class TasksService {
  constructor(@InjectRepository(Task) private readonly repo: Repository<Task>) {}

  findAll(): Promise<Task[]> {
    return this.repo.find({ order: { createdAt: 'DESC' } });
  }

  create(body: CreateTaskDto): Promise<Task> {
    return this.repo.save(
      this.repo.create({
        subject: body.subject,
        description: body.description ?? null,
        notes: body.notes ?? null,
        status: body.status ?? 'todo',
      }),
    );
  }

  async update(id: number, body: UpdateTaskDto): Promise<Task> {
    const task = await this.repo.findOne({ where: { id } });
    if (!task) throw new NotFoundException(`Task ${id} not found`);
    Object.assign(task, body);
    return this.repo.save(task);
  }

  async remove(id: number): Promise<void> {
    const task = await this.repo.findOne({ where: { id } });
    if (!task) throw new NotFoundException(`Task ${id} not found`);
    await this.repo.remove(task);
  }
}
```

**Step 3: Verify backend still compiles**

Run from `~/Projects/BalanceTracker/server/`:
```bash
npm run build
```
Expected: `dist/` rebuilt with no TypeScript errors.

**Step 4: Commit**

```bash
cd ~/Projects/BalanceTracker
git add server/src/entities/task.entity.ts server/src/tasks/tasks.service.ts
git commit -m "feat(tasks): add subject and status fields to Task entity"
```

---

### Task 2: Create Note entity and Notes module

**Files:**
- Create: `~/Projects/BalanceTracker/server/src/entities/note.entity.ts`
- Create: `~/Projects/BalanceTracker/server/src/notes/notes.module.ts`
- Create: `~/Projects/BalanceTracker/server/src/notes/notes.service.ts`
- Create: `~/Projects/BalanceTracker/server/src/notes/notes.controller.ts`

**Step 1: Create note.entity.ts**

```typescript
import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('note')
export class Note {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'text' })
  title: string;

  @Column({ type: 'text', nullable: true })
  content: string | null;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
```

**Step 2: Create notes.service.ts**

```typescript
import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Note } from '../entities/note.entity.js';

@Injectable()
export class NotesService {
  constructor(@InjectRepository(Note) private readonly repo: Repository<Note>) {}

  findAll(): Promise<Note[]> {
    return this.repo.find({ order: { updatedAt: 'DESC' } });
  }

  create(body: { title: string; content?: string | null }): Promise<Note> {
    return this.repo.save(
      this.repo.create({ title: body.title, content: body.content ?? null }),
    );
  }

  async update(id: number, body: { title?: string; content?: string | null }): Promise<Note> {
    const note = await this.repo.findOne({ where: { id } });
    if (!note) throw new NotFoundException(`Note ${id} not found`);
    Object.assign(note, body);
    return this.repo.save(note);
  }

  async remove(id: number): Promise<void> {
    const note = await this.repo.findOne({ where: { id } });
    if (!note) throw new NotFoundException(`Note ${id} not found`);
    await this.repo.remove(note);
  }
}
```

**Step 3: Create notes.controller.ts**

```typescript
import { Controller, Get, Post, Put, Delete, Param, Body, ParseIntPipe, UseGuards } from '@nestjs/common';
import { NotesService } from './notes.service.js';
import { GoogleTokenGuard } from '../guards/google-token.guard.js';

@Controller('notes')
@UseGuards(GoogleTokenGuard)
export class NotesController {
  constructor(private readonly notesService: NotesService) {}

  @Get()
  findAll() {
    return this.notesService.findAll();
  }

  @Post()
  create(@Body() body: any) {
    return this.notesService.create(body);
  }

  @Put(':id')
  update(@Param('id', ParseIntPipe) id: number, @Body() body: any) {
    return this.notesService.update(id, body);
  }

  @Delete(':id')
  remove(@Param('id', ParseIntPipe) id: number) {
    return this.notesService.remove(id);
  }
}
```

**Step 4: Create notes.module.ts**

```typescript
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { NotesController } from './notes.controller.js';
import { NotesService } from './notes.service.js';
import { Note } from '../entities/note.entity.js';

@Module({
  imports: [TypeOrmModule.forFeature([Note])],
  controllers: [NotesController],
  providers: [NotesService],
})
export class NotesModule {}
```

**Step 5: Compile check**

```bash
cd ~/Projects/BalanceTracker/server && npm run build
```
Expected: no errors.

**Step 6: Commit**

```bash
cd ~/Projects/BalanceTracker
git add server/src/entities/note.entity.ts server/src/notes/
git commit -m "feat(notes): add Note entity and NotesModule"
```

---

### Task 3: Wire Notes into app.module.ts and smoke-test

**Files:**
- Modify: `~/Projects/BalanceTracker/server/src/app.module.ts`

**Step 1: Add Note entity to TypeORM entities array**

In `app.module.ts`, add to the imports at the top:
```typescript
import { Note } from './entities/note.entity.js';
import { NotesModule } from './notes/notes.module.js';
```

In the `TypeOrmModule.forRoot({ entities: [...] })` array, add `Note` after `Task`:
```typescript
Task,
Note,
SyncSettings,
```

In the `imports` array of `@Module`, add `NotesModule` after `TasksModule`:
```typescript
TasksModule,
NotesModule,
```

**Step 2: Start the backend and test endpoints**

```bash
cd ~/Projects/BalanceTracker/server && npm run start:dev
```

In a second terminal, test with curl (replace TOKEN with a real Google ID token):
```bash
curl -H "Authorization: Bearer TOKEN" http://localhost:3000/notes
# Expected: []

curl -X POST -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Test Note","content":"Hello"}' http://localhost:3000/notes
# Expected: {"id":1,"title":"Test Note","content":"Hello","createdAt":"...","updatedAt":"..."}

curl -H "Authorization: Bearer TOKEN" http://localhost:3000/tasks
# Expected: array (existing tasks)
```

**Step 3: Commit**

```bash
cd ~/Projects/BalanceTracker
git add server/src/app.module.ts
git commit -m "feat: wire NotesModule into AppModule"
```

---

## Phase 2 — Tray App: Project Scaffold

### Task 4: Create project structure

**Files:**
- Create: `~/Projects/Desktop_Mike/balancetracker-tray/` (directory tree)

**Step 1: Create all directories and placeholder files**

```bash
cd ~/Projects/Desktop_Mike
mkdir -p balancetracker-tray/{api,panels,assets,tests}
touch balancetracker-tray/{app.py,window.py,config.py,style.css}
touch balancetracker-tray/api/{__init__.py,client.py,tasks.py,notes.py}
touch balancetracker-tray/panels/{__init__.py,tasks.py,notes.py,chat.py}
touch balancetracker-tray/tests/{__init__.py,test_config.py,test_api_client.py,test_api_tasks.py,test_api_notes.py}
touch balancetracker-tray/__init__.py
```

**Step 2: Create requirements.txt**

```
PyGObject>=3.42.0
requests>=2.28.0
anthropic>=0.25.0
```

**Step 3: Create .gitignore**

```
.venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
```

**Step 4: Create the tray icon**

Create a minimal 22×22 green circle PNG as `assets/icon.png`. The simplest approach is to use Python + cairo to generate it:

```bash
cd ~/Projects/Desktop_Mike/balancetracker-tray
python3 - <<'EOF'
import cairo
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 22, 22)
cr = cairo.Context(surface)
cr.set_source_rgba(0, 0.78, 0.32, 1.0)  # #00C853
cr.arc(11, 11, 9, 0, 2 * 3.14159)
cr.fill()
surface.write_to_png("assets/icon.png")
print("icon created")
EOF
```
Expected: `assets/icon.png` created.

**Step 5: Commit scaffold**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/
git commit -m "feat(tray): scaffold project structure"
```

---

## Phase 3 — Core Infrastructure

### Task 5: config.py

**Files:**
- Modify: `balancetracker-tray/config.py`
- Modify: `balancetracker-tray/tests/test_config.py`

**Step 1: Write the failing tests first**

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
cd ~/Projects/Desktop_Mike/balancetracker-tray
python3 -m pytest tests/test_config.py -v
```
Expected: ImportError or AttributeError — config module is empty.

**Step 3: Implement config.py**

```python
import json
import os

CONFIG_PATH = os.path.expanduser('~/.config/balancetracker-tray/config.json')

DEFAULTS = {
    'bearer_token': '',
    'anthropic_api_key': '',
    'claude_model': 'claude-haiku-4-5-20251001',
    'backend_url': 'http://localhost:3000',
}

def load_config(path: str = CONFIG_PATH) -> dict:
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULTS)

def save_config(data: dict, path: str = CONFIG_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_config.py -v
```
Expected: 3 tests PASSED.

**Step 5: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/config.py balancetracker-tray/tests/test_config.py
git commit -m "feat(tray): add config loader"
```

---

### Task 6: api/client.py

**Files:**
- Modify: `balancetracker-tray/api/client.py`
- Modify: `balancetracker-tray/tests/test_api_client.py`

**Step 1: Write failing tests**

```python
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
```

**Step 2: Run to verify failure**

```bash
cd ~/Projects/Desktop_Mike/balancetracker-tray
python3 -m pytest tests/test_api_client.py -v
```
Expected: ImportError.

**Step 3: Implement api/client.py**

```python
import requests

class ApiClient:
    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url.rstrip('/')
        self.bearer_token = bearer_token

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
        }

    def _handle_response(self, resp: requests.Response):
        if resp.status_code == 401:
            raise PermissionError('Bearer token rejected (401). Update config.json and restart.')
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return None

    def get(self, path: str):
        try:
            resp = requests.get(f'{self.base_url}{path}', headers=self._headers(), timeout=10)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend at {self.base_url}: {e}')

    def post(self, path: str, body: dict):
        try:
            resp = requests.post(f'{self.base_url}{path}', headers=self._headers(), json=body, timeout=10)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend: {e}')

    def put(self, path: str, body: dict):
        try:
            resp = requests.put(f'{self.base_url}{path}', headers=self._headers(), json=body, timeout=10)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend: {e}')

    def delete(self, path: str):
        try:
            resp = requests.delete(f'{self.base_url}{path}', headers=self._headers(), timeout=10)
            return self._handle_response(resp)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'Cannot reach backend: {e}')
```

**Step 4: Run tests to verify pass**

```bash
python3 -m pytest tests/test_api_client.py -v
```
Expected: 4 tests PASSED.

**Step 5: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/api/client.py balancetracker-tray/tests/test_api_client.py
git commit -m "feat(tray): add ApiClient base class"
```

---

### Task 7: api/tasks.py and api/notes.py

**Files:**
- Modify: `balancetracker-tray/api/tasks.py`
- Modify: `balancetracker-tray/api/notes.py`
- Modify: `balancetracker-tray/tests/test_api_tasks.py`
- Modify: `balancetracker-tray/tests/test_api_notes.py`

**Step 1: Write tests for tasks API wrapper**

```python
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
```

```python
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
```

**Step 2: Run tests to verify failure**

```bash
python3 -m pytest tests/test_api_tasks.py tests/test_api_notes.py -v
```
Expected: ImportError.

**Step 3: Implement api/tasks.py**

```python
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
```

**Step 4: Implement api/notes.py**

```python
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
```

**Step 5: Run all tests**

```bash
python3 -m pytest tests/ -v
```
Expected: all 11 tests PASSED.

**Step 6: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/api/tasks.py balancetracker-tray/api/notes.py \
        balancetracker-tray/tests/test_api_tasks.py balancetracker-tray/tests/test_api_notes.py
git commit -m "feat(tray): add tasks and notes API wrappers"
```

---

## Phase 4 — Styling

### Task 8: style.css

**Files:**
- Modify: `balancetracker-tray/style.css`

**Step 1: Write the CSS**

```css
/* style.css — BalanceTracker Tray: dark translucent theme */

* {
    font-family: Monospace;
    font-size: 9pt;
    color: #cccccc;
}

window {
    background-color: transparent;
}

/* Main content box — the translucent panel */
.main-box {
    background-color: rgba(10, 10, 10, 0.88);
    border: 1px solid #00C853;
    border-radius: 6px;
    padding: 4px;
}

/* Notebook tabs */
notebook tab {
    background-color: rgba(20, 20, 20, 0.9);
    padding: 4px 10px;
    color: #888888;
    border: none;
}

notebook tab:checked {
    background-color: rgba(0, 200, 83, 0.15);
    color: #00C853;
    border-bottom: 2px solid #00C853;
}

/* Scrolled windows — transparent */
scrolledwindow {
    background-color: transparent;
}

viewport {
    background-color: transparent;
}

/* Task rows */
.task-row {
    background-color: rgba(255, 255, 255, 0.04);
    border-radius: 4px;
    padding: 6px 8px;
    margin: 2px 0;
}

.task-row:hover {
    background-color: rgba(0, 200, 83, 0.08);
}

.task-subject {
    color: #ffffff;
    font-weight: bold;
}

/* Status badges */
.status-todo {
    color: #888888;
    font-size: 8pt;
}

.status-in_progress {
    color: #FFD600;
    font-size: 8pt;
}

.status-done {
    color: #00C853;
    font-size: 8pt;
}

/* Note rows */
.note-row {
    background-color: rgba(255, 255, 255, 0.04);
    border-radius: 4px;
    padding: 6px 8px;
    margin: 2px 0;
}

.note-row:checked,
.note-row:selected {
    background-color: rgba(0, 200, 83, 0.15);
    color: #00C853;
}

/* Chat messages */
.chat-user {
    color: #00C853;
    text-align: right;
    margin: 4px 0 4px 40px;
    font-style: italic;
}

.chat-assistant {
    color: #cccccc;
    margin: 4px 40px 4px 0;
}

.chat-error {
    color: #FF5252;
    font-size: 8pt;
}

/* Inputs */
entry {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid #333333;
    border-radius: 3px;
    color: #ffffff;
    padding: 4px 6px;
    caret-color: #00C853;
}

entry:focus {
    border-color: #00C853;
    box-shadow: 0 0 0 1px rgba(0, 200, 83, 0.3);
}

textview {
    background-color: rgba(255, 255, 255, 0.04);
    color: #cccccc;
    border: 1px solid #222222;
    border-radius: 3px;
}

textview:focus {
    border-color: #00C853;
}

/* Buttons */
button {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid #333333;
    border-radius: 3px;
    color: #cccccc;
    padding: 3px 8px;
    min-height: 0;
}

button:hover {
    background-color: rgba(0, 200, 83, 0.15);
    border-color: #00C853;
    color: #00C853;
}

button.accent {
    background-color: rgba(0, 200, 83, 0.2);
    border-color: #00C853;
    color: #00C853;
}

/* Error banner */
.error-bar {
    background-color: rgba(255, 82, 82, 0.2);
    border: 1px solid #FF5252;
    border-radius: 3px;
    padding: 4px 8px;
    color: #FF5252;
    font-size: 8pt;
}

/* Separator */
separator {
    background-color: #222222;
}
```

**Step 2: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/style.css
git commit -m "feat(tray): add dark/green CSS theme"
```

---

## Phase 5 — UI Panels

### Task 9: panels/tasks.py

**Files:**
- Modify: `balancetracker-tray/panels/tasks.py`

**Step 1: Implement tasks panel**

```python
# panels/tasks.py
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

STATUS_LABELS = {
    'todo': '[todo]',
    'in_progress': '[in_progress]',
    'done': '[done]',
}

class TasksPanel(Gtk.Box):
    def __init__(self, tasks_api):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.tasks_api = tasks_api
        self.tasks = []
        self.expanded_id = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header bar with title and add button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label = Gtk.Label(label='Tasks')
        label.get_style_context().add_class('task-subject')
        label.set_halign(Gtk.Align.START)
        header.pack_start(label, True, True, 0)
        add_btn = Gtk.Button(label='+')
        add_btn.get_style_context().add_class('accent')
        add_btn.connect('clicked', self._show_create_form)
        header.pack_end(add_btn, False, False, 0)
        self.pack_start(header, False, False, 4)

        # Error label (hidden by default)
        self.error_label = Gtk.Label(label='')
        self.error_label.get_style_context().add_class('error-bar')
        self.error_label.set_no_show_all(True)
        self.pack_start(self.error_label, False, False, 0)

        # Create form (hidden by default)
        self.create_form = self._build_create_form()
        self.create_form.set_no_show_all(True)
        self.pack_start(self.create_form, False, False, 0)

        # Scrollable task list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.list_box)
        self.pack_start(scroll, True, True, 0)

    def _build_create_form(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.get_style_context().add_class('task-row')

        self.new_subject = Gtk.Entry()
        self.new_subject.set_placeholder_text('Subject (required)')
        box.pack_start(self.new_subject, False, False, 0)

        self.new_description = Gtk.Entry()
        self.new_description.set_placeholder_text('Description')
        box.pack_start(self.new_description, False, False, 0)

        self.new_notes = Gtk.Entry()
        self.new_notes.set_placeholder_text('Notes')
        box.pack_start(self.new_notes, False, False, 0)

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        status_label = Gtk.Label(label='Status:')
        self.new_status = Gtk.ComboBoxText()
        for s in ('todo', 'in_progress', 'done'):
            self.new_status.append_text(s)
        self.new_status.set_active(0)
        status_box.pack_start(status_label, False, False, 0)
        status_box.pack_start(self.new_status, True, True, 0)
        box.pack_start(status_box, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        save_btn = Gtk.Button(label='Save')
        save_btn.get_style_context().add_class('accent')
        save_btn.connect('clicked', self._do_create)
        cancel_btn = Gtk.Button(label='Cancel')
        cancel_btn.connect('clicked', lambda _: self.create_form.hide())
        btn_box.pack_start(save_btn, True, True, 0)
        btn_box.pack_start(cancel_btn, True, True, 0)
        box.pack_start(btn_box, False, False, 0)

        return box

    def _show_create_form(self, _):
        self.new_subject.set_text('')
        self.new_description.set_text('')
        self.new_notes.set_text('')
        self.new_status.set_active(0)
        self.create_form.show()

    def _do_create(self, _):
        subject = self.new_subject.get_text().strip()
        if not subject:
            return
        description = self.new_description.get_text().strip() or None
        notes = self.new_notes.get_text().strip() or None
        status = self.new_status.get_active_text()
        self.create_form.hide()
        self._run_async(
            lambda: self.tasks_api.create(subject, description=description, notes=notes, status=status),
            on_success=lambda _: self.refresh(),
        )

    def refresh(self):
        self._run_async(self.tasks_api.get_all, on_success=self._on_tasks_loaded)

    def _on_tasks_loaded(self, tasks):
        self.tasks = tasks
        for child in self.list_box.get_children():
            self.list_box.remove(child)
        for task in tasks:
            row = self._build_task_row(task)
            self.list_box.add(row)
        self.list_box.show_all()

    def _build_task_row(self, task):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        outer.get_style_context().add_class('task-row')

        # Summary line
        summary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_css = f'status-{task.get("status","todo")}'
        status_lbl = Gtk.Label(label=STATUS_LABELS.get(task.get('status','todo'), ''))
        status_lbl.get_style_context().add_class(status_css)
        subject_lbl = Gtk.Label(label=task.get('subject', ''))
        subject_lbl.get_style_context().add_class('task-subject')
        subject_lbl.set_halign(Gtk.Align.START)
        subject_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END

        expand_btn = Gtk.Button(label='▸')
        expand_btn.set_relief(Gtk.ReliefStyle.NONE)

        summary.pack_start(status_lbl, False, False, 0)
        summary.pack_start(subject_lbl, True, True, 0)
        summary.pack_end(expand_btn, False, False, 0)
        outer.pack_start(summary, False, False, 0)

        # Detail section (hidden by default)
        detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        detail.set_no_show_all(True)

        if task.get('description'):
            desc_lbl = Gtk.Label(label=task['description'])
            desc_lbl.set_line_wrap(True)
            desc_lbl.set_halign(Gtk.Align.START)
            detail.pack_start(desc_lbl, False, False, 0)

        if task.get('notes'):
            notes_lbl = Gtk.Label(label=f'Notes: {task["notes"]}')
            notes_lbl.set_line_wrap(True)
            notes_lbl.set_halign(Gtk.Align.START)
            detail.pack_start(notes_lbl, False, False, 0)

        # Status change dropdown
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        combo = Gtk.ComboBoxText()
        for s in ('todo', 'in_progress', 'done'):
            combo.append_text(s)
        active_idx = {'todo': 0, 'in_progress': 1, 'done': 2}.get(task.get('status', 'todo'), 0)
        combo.set_active(active_idx)
        combo.connect('changed', lambda c, t=task: self._update_status(t['id'], c.get_active_text()))
        status_row.pack_start(Gtk.Label(label='Status:'), False, False, 0)
        status_row.pack_start(combo, True, True, 0)

        delete_btn = Gtk.Button(label='Delete')
        delete_btn.connect('clicked', lambda _, t=task: self._delete_task(t['id']))
        status_row.pack_end(delete_btn, False, False, 0)

        detail.pack_start(status_row, False, False, 0)
        outer.pack_start(detail, False, False, 0)

        def toggle_detail(_btn):
            if detail.get_visible():
                detail.hide()
                _btn.set_label('▸')
            else:
                detail.show_all()
                _btn.set_label('▾')

        expand_btn.connect('clicked', toggle_detail)
        return outer

    def _update_status(self, task_id, status):
        self._run_async(
            lambda: self.tasks_api.update(task_id, status=status),
            on_success=lambda _: self.refresh(),
        )

    def _delete_task(self, task_id):
        self._run_async(
            lambda: self.tasks_api.delete(task_id),
            on_success=lambda _: self.refresh(),
        )

    def _run_async(self, fn, on_success=None):
        def worker():
            try:
                result = fn()
                if on_success:
                    GLib.idle_add(on_success, result)
                GLib.idle_add(self.error_label.hide)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _show_error(self, msg):
        self.error_label.set_text(msg)
        self.error_label.show()
```

**Step 2: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/panels/tasks.py
git commit -m "feat(tray): add Tasks panel"
```

---

### Task 10: panels/notes.py

**Files:**
- Modify: `balancetracker-tray/panels/notes.py`

**Step 1: Implement notes panel**

```python
# panels/notes.py
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class NotesPanel(Gtk.Box):
    def __init__(self, notes_api):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.notes_api = notes_api
        self.notes = []
        self.selected_note = None
        self._save_timer = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label = Gtk.Label(label='Notes')
        label.set_halign(Gtk.Align.START)
        header.pack_start(label, True, True, 0)
        add_btn = Gtk.Button(label='+')
        add_btn.get_style_context().add_class('accent')
        add_btn.connect('clicked', self._create_note_dialog)
        header.pack_end(add_btn, False, False, 0)
        self.pack_start(header, False, False, 4)

        # Error label
        self.error_label = Gtk.Label(label='')
        self.error_label.get_style_context().add_class('error-bar')
        self.error_label.set_no_show_all(True)
        self.pack_start(self.error_label, False, False, 0)

        # Two-pane layout
        paned = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.pack_start(paned, True, True, 0)

        # Left: note list (fixed width)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_size_request(140, -1)
        scroll_left = Gtk.ScrolledWindow()
        scroll_left.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.notes_listbox = Gtk.ListBox()
        self.notes_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.notes_listbox.connect('row-selected', self._on_note_selected)
        scroll_left.add(self.notes_listbox)
        left.pack_start(scroll_left, True, True, 0)
        paned.pack_start(left, False, False, 0)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        paned.pack_start(sep, False, False, 0)

        # Right: content editor
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.content_label = Gtk.Label(label='Select a note')
        self.content_label.set_halign(Gtk.Align.CENTER)
        self.content_label.set_valign(Gtk.Align.CENTER)

        scroll_right = Gtk.ScrolledWindow()
        scroll_right.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.content_view = Gtk.TextView()
        self.content_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.content_view.get_buffer().connect('changed', self._on_content_changed)
        self.content_view.set_sensitive(False)
        scroll_right.add(self.content_view)

        self.delete_btn = Gtk.Button(label='Delete Note')
        self.delete_btn.connect('clicked', self._delete_selected)
        self.delete_btn.set_sensitive(False)

        right.pack_start(scroll_right, True, True, 0)
        right.pack_start(self.delete_btn, False, False, 0)
        paned.pack_start(right, True, True, 0)

    def refresh(self):
        def do_fetch():
            try:
                notes = self.notes_api.get_all()
                GLib.idle_add(self._on_notes_loaded, notes)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
        threading.Thread(target=do_fetch, daemon=True).start()

    def _on_notes_loaded(self, notes):
        self.notes = notes
        for child in self.notes_listbox.get_children():
            self.notes_listbox.remove(child)
        for note in notes:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class('note-row')
            lbl = Gtk.Label(label=note.get('title', ''))
            lbl.set_halign(Gtk.Align.START)
            lbl.set_ellipsize(3)
            lbl.set_xalign(0)
            lbl.set_padding(6, 4)
            row.add(lbl)
            row.note_data = note
            self.notes_listbox.add(row)
        self.notes_listbox.show_all()

    def _on_note_selected(self, _listbox, row):
        if row is None:
            self.selected_note = None
            self.content_view.set_sensitive(False)
            self.delete_btn.set_sensitive(False)
            return
        self.selected_note = row.note_data
        buf = self.content_view.get_buffer()
        buf.handler_block_by_func(self._on_content_changed)
        buf.set_text(self.selected_note.get('content') or '')
        buf.handler_unblock_by_func(self._on_content_changed)
        self.content_view.set_sensitive(True)
        self.delete_btn.set_sensitive(True)

    def _on_content_changed(self, buf):
        if self.selected_note is None:
            return
        if self._save_timer:
            GLib.source_remove(self._save_timer)
        self._save_timer = GLib.timeout_add(1500, self._auto_save)

    def _auto_save(self):
        self._save_timer = None
        if self.selected_note is None:
            return False
        buf = self.content_view.get_buffer()
        content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        note_id = self.selected_note['id']
        def do_save():
            try:
                self.notes_api.update(note_id, content=content)
                GLib.idle_add(self.error_label.hide)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
        threading.Thread(target=do_save, daemon=True).start()
        return False

    def _create_note_dialog(self, _):
        dialog = Gtk.Dialog(title='New Note', modal=True)
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Create', Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_placeholder_text('Note title')
        dialog.get_content_area().pack_start(entry, False, False, 8)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            title = entry.get_text().strip()
            if title:
                def do_create():
                    try:
                        self.notes_api.create(title)
                        GLib.idle_add(self.refresh)
                    except Exception as e:
                        GLib.idle_add(self._show_error, str(e))
                threading.Thread(target=do_create, daemon=True).start()
        dialog.destroy()

    def _delete_selected(self, _):
        if self.selected_note is None:
            return
        note_id = self.selected_note['id']
        self.selected_note = None
        self.content_view.set_sensitive(False)
        self.delete_btn.set_sensitive(False)
        def do_delete():
            try:
                self.notes_api.delete(note_id)
                GLib.idle_add(self.refresh)
            except Exception as e:
                GLib.idle_add(self._show_error, str(e))
        threading.Thread(target=do_delete, daemon=True).start()

    def _show_error(self, msg):
        self.error_label.set_text(msg)
        self.error_label.show()
```

**Step 2: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/panels/notes.py
git commit -m "feat(tray): add Notes panel"
```

---

### Task 11: panels/chat.py

**Files:**
- Modify: `balancetracker-tray/panels/chat.py`

**Step 1: Implement chat panel**

```python
# panels/chat.py
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import anthropic

class ChatPanel(Gtk.Box):
    def __init__(self, config: dict):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.config = config
        self.history = []  # list of {"role": "user"|"assistant", "content": "..."}
        self._build_ui()

    def _build_ui(self):
        # Header
        header = Gtk.Label(label='Claude Chat')
        header.set_halign(Gtk.Align.START)
        self.pack_start(header, False, False, 4)

        # Error label
        self.error_label = Gtk.Label(label='')
        self.error_label.get_style_context().add_class('error-bar')
        self.error_label.set_no_show_all(True)
        self.pack_start(self.error_label, False, False, 0)

        # Chat history scroll area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.history_box.set_margin_start(4)
        self.history_box.set_margin_end(4)
        scroll.add(self.history_box)
        self.scroll = scroll
        self.pack_start(scroll, True, True, 0)

        # Input row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.input_entry = Gtk.Entry()
        self.input_entry.set_placeholder_text('Ask Claude...')
        self.input_entry.connect('activate', self._send)
        send_btn = Gtk.Button(label='Send')
        send_btn.get_style_context().add_class('accent')
        send_btn.connect('clicked', self._send)
        clear_btn = Gtk.Button(label='Clear')
        clear_btn.connect('clicked', self._clear)
        input_row.pack_start(self.input_entry, True, True, 0)
        input_row.pack_start(send_btn, False, False, 0)
        input_row.pack_start(clear_btn, False, False, 0)
        self.pack_start(input_row, False, False, 4)

    def _add_message(self, role: str, text: str):
        """Add a message bubble to the history box. Must be called from GTK main thread."""
        lbl = Gtk.Label(label=text)
        lbl.set_line_wrap(True)
        lbl.set_xalign(1.0 if role == 'user' else 0.0)
        lbl.set_selectable(True)
        if role == 'user':
            lbl.get_style_context().add_class('chat-user')
        elif role == 'error':
            lbl.get_style_context().add_class('chat-error')
        else:
            lbl.get_style_context().add_class('chat-assistant')
        self.history_box.pack_start(lbl, False, False, 0)
        lbl.show()
        # Scroll to bottom
        adj = self.scroll.get_vadjustment()
        adj.set_value(adj.get_upper())

    def _send(self, _widget):
        text = self.input_entry.get_text().strip()
        if not text:
            return
        self.input_entry.set_text('')
        self.history.append({'role': 'user', 'content': text})
        self._add_message('user', text)
        self.error_label.hide()

        # Show a "..." placeholder while waiting
        waiting_lbl = Gtk.Label(label='...')
        waiting_lbl.get_style_context().add_class('chat-assistant')
        waiting_lbl.set_xalign(0.0)
        self.history_box.pack_start(waiting_lbl, False, False, 0)
        waiting_lbl.show()

        def do_request():
            try:
                client = anthropic.Anthropic(api_key=self.config.get('anthropic_api_key', ''))
                response = client.messages.create(
                    model=self.config.get('claude_model', 'claude-haiku-4-5-20251001'),
                    max_tokens=1024,
                    messages=self.history,
                )
                reply = response.content[0].text
                self.history.append({'role': 'assistant', 'content': reply})
                GLib.idle_add(self._on_reply, waiting_lbl, reply)
            except anthropic.AuthenticationError:
                GLib.idle_add(self._on_error, waiting_lbl, 'Invalid Anthropic API key.')
            except Exception as e:
                GLib.idle_add(self._on_error, waiting_lbl, f'Error: {e}')

        threading.Thread(target=do_request, daemon=True).start()

    def _on_reply(self, waiting_lbl, reply):
        self.history_box.remove(waiting_lbl)
        self._add_message('assistant', reply)

    def _on_error(self, waiting_lbl, msg):
        self.history_box.remove(waiting_lbl)
        self._add_message('error', msg)

    def _clear(self, _):
        self.history.clear()
        for child in self.history_box.get_children():
            self.history_box.remove(child)
```

**Step 2: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/panels/chat.py
git commit -m "feat(tray): add Claude chat panel"
```

---

## Phase 6 — Main Window and AppIndicator

### Task 12: window.py

**Files:**
- Modify: `balancetracker-tray/window.py`

**Step 1: Implement main window**

```python
# window.py
import os
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
import cairo
from gi.repository import Gtk, Gdk, GLib

from config import load_config
from api.client import ApiClient
from api.tasks import TasksApi
from api.notes import NotesApi
from panels.tasks import TasksPanel
from panels.notes import NotesPanel
from panels.chat import ChatPanel

class TrayWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.config = load_config()
        self._setup_window()
        self._setup_transparency()
        self._setup_api()
        self._load_css()
        self._build_ui()
        self.connect('key-press-event', self._on_key_press)
        self.connect('delete-event', lambda w, e: w.hide() or True)

    def _setup_window(self):
        screen = Gdk.Screen.get_default()
        sw = screen.get_width()
        sh = screen.get_height()
        # Size: width/4 * height/2 = width*height/8
        w = sw // 4
        h = sh // 2
        self.set_default_size(w, h)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        # Position: top-right, below the GNOME top bar (~30px)
        self.move(sw - w - 8, 32)

    def _setup_transparency(self):
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect('draw', self._on_draw)

    def _on_draw(self, widget, cr):
        cr.set_source_rgba(0.039, 0.039, 0.039, 0.88)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

    def _setup_api(self):
        client = ApiClient(
            base_url=self.config.get('backend_url', 'http://localhost:3000'),
            bearer_token=self.config.get('bearer_token', ''),
        )
        self.tasks_api = TasksApi(client)
        self.notes_api = NotesApi(client)

    def _load_css(self):
        css_path = os.path.join(os.path.dirname(__file__), 'style.css')
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.get_style_context().add_class('main-box')
        outer.set_margin_start(4)
        outer.set_margin_end(4)
        outer.set_margin_top(4)
        outer.set_margin_bottom(4)

        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)

        tasks_panel = TasksPanel(self.tasks_api)
        tasks_panel.set_margin_start(6)
        tasks_panel.set_margin_end(6)
        tasks_panel.set_margin_top(6)
        notebook.append_page(tasks_panel, Gtk.Label(label='Tasks'))

        notes_panel = NotesPanel(self.notes_api)
        notes_panel.set_margin_start(6)
        notes_panel.set_margin_end(6)
        notes_panel.set_margin_top(6)
        notebook.append_page(notes_panel, Gtk.Label(label='Notes'))

        chat_panel = ChatPanel(self.config)
        chat_panel.set_margin_start(6)
        chat_panel.set_margin_end(6)
        chat_panel.set_margin_top(6)
        notebook.append_page(chat_panel, Gtk.Label(label='Chat'))

        # Refresh tasks/notes when their tab is switched to
        notebook.connect('switch-page', self._on_tab_switch,
                         tasks_panel, notes_panel)

        outer.pack_start(notebook, True, True, 0)
        self.add(outer)
        self.show_all()

    def _on_tab_switch(self, notebook, page, page_num, tasks_panel, notes_panel):
        if page_num == 0:
            tasks_panel.refresh()
        elif page_num == 1:
            notes_panel.refresh()

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()
            self.present()
```

**Step 2: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/window.py
git commit -m "feat(tray): add main translucent window"
```

---

### Task 13: app.py (AppIndicator entry point)

**Files:**
- Modify: `balancetracker-tray/app.py`

**Step 1: Implement app.py**

```python
#!/usr/bin/env python3
# app.py — BalanceTracker Tray App entry point
import os
import sys
import signal
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AppIndicator3

from window import TrayWindow
from config import load_config, save_config, CONFIG_PATH

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
ICON_PATH = os.path.join(ASSETS_DIR, 'icon.png')

def main():
    # Allow Ctrl+C to terminate cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Ensure config exists; prompt user if not
    config = load_config()
    if not config.get('bearer_token') or not config.get('anthropic_api_key'):
        _show_setup_dialog(config)

    # Create the main window (hidden initially)
    window = TrayWindow()
    window.hide()

    # Create the AppIndicator
    indicator = AppIndicator3.Indicator.new(
        'balancetracker-tray',
        ICON_PATH,
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    indicator.set_title('BalanceTracker')

    # Build a minimal menu that immediately toggles the window and hides itself
    menu = Gtk.Menu()

    def on_menu_show(m):
        m.hide()
        GLib.idle_add(window.toggle)

    menu.connect('show', on_menu_show)

    # Fallback item (never visible normally, but menu must be non-empty)
    item = Gtk.MenuItem(label='BalanceTracker')
    item.connect('activate', lambda _: window.toggle())
    menu.append(item)

    quit_item = Gtk.SeparatorMenuItem()
    menu.append(quit_item)
    quit_item2 = Gtk.MenuItem(label='Quit')
    quit_item2.connect('activate', lambda _: Gtk.main_quit())
    menu.append(quit_item2)

    menu.show_all()
    indicator.set_menu(menu)

    Gtk.main()


def _show_setup_dialog(config: dict):
    dialog = Gtk.Dialog(title='BalanceTracker Tray — Setup')
    dialog.add_buttons('Save', Gtk.ResponseType.OK, 'Skip', Gtk.ResponseType.CANCEL)
    box = dialog.get_content_area()

    token_entry = Gtk.Entry()
    token_entry.set_placeholder_text('Google ID Token (Bearer)')
    token_entry.set_text(config.get('bearer_token', ''))
    token_entry.set_width_chars(50)

    api_key_entry = Gtk.Entry()
    api_key_entry.set_placeholder_text('Anthropic API Key (sk-ant-...)')
    api_key_entry.set_text(config.get('anthropic_api_key', ''))
    api_key_entry.set_width_chars(50)

    box.pack_start(Gtk.Label(label='Bearer Token:'), False, False, 4)
    box.pack_start(token_entry, False, False, 4)
    box.pack_start(Gtk.Label(label='Anthropic API Key:'), False, False, 4)
    box.pack_start(api_key_entry, False, False, 4)
    dialog.show_all()

    if dialog.run() == Gtk.ResponseType.OK:
        config['bearer_token'] = token_entry.get_text().strip()
        config['anthropic_api_key'] = api_key_entry.get_text().strip()
        save_config(config)
    dialog.destroy()


if __name__ == '__main__':
    main()
```

**Step 2: Commit**

```bash
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/app.py
git commit -m "feat(tray): add AppIndicator entry point"
```

---

## Phase 7 — Deployment

### Task 14: systemd service file and install.sh

**Files:**
- Create: `balancetracker-tray/balancetracker-tray.service`
- Create: `balancetracker-tray/install.sh`

**Step 1: Create the systemd unit template**

```ini
# balancetracker-tray.service
[Unit]
Description=BalanceTracker Tray App
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=VENV_PYTHON_PLACEHOLDER app.py
WorkingDirectory=APP_DIR_PLACEHOLDER
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=graphical-session.target
```

**Step 2: Create install.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="balancetracker-tray.service"

echo "==> Installing BalanceTracker Tray App"
echo ""

# 1. Check system dependencies
echo "--- Checking system dependencies ---"
MISSING=()
python3 -c "import gi" 2>/dev/null || MISSING+=("python3-gobject")
pkg-config --exists ayatana-appindicator3-0.1 2>/dev/null || \
  pkg-config --exists appindicator3-0.1 2>/dev/null || MISSING+=("libayatana-appindicator-gtk3")

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "Missing system packages: ${MISSING[*]}"
  echo "Run: sudo dnf install ${MISSING[*]}"
  exit 1
fi
echo "System dependencies OK."

# 2. Create Python venv
echo ""
echo "--- Creating Python virtual environment ---"
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$SCRIPT_DIR/.venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "venv ready at $SCRIPT_DIR/.venv"

# 3. Install systemd user service
echo ""
echo "--- Installing systemd user service ---"
mkdir -p "$SERVICE_DIR"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
sed \
  -e "s|VENV_PYTHON_PLACEHOLDER|$VENV_PYTHON|g" \
  -e "s|APP_DIR_PLACEHOLDER|$SCRIPT_DIR|g" \
  "$SCRIPT_DIR/balancetracker-tray.service" > "$SERVICE_DIR/$SERVICE_NAME"

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"
echo "Service enabled and started."

# 4. Check for AppIndicator GNOME extension
echo ""
echo "--- Checking GNOME AppIndicator extension ---"
if gnome-extensions list 2>/dev/null | grep -q "appindicatorsupport"; then
  gnome-extensions enable "appindicatorsupport@rgcjonas.gmail.com" 2>/dev/null || true
  echo "AppIndicator extension enabled."
else
  echo "NOTICE: gnome-shell-extension-appindicator not found."
  echo "Install it with:"
  echo "  sudo dnf install gnome-shell-extension-appindicator"
  echo "  gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com"
  echo "  (then log out and back in)"
fi

echo ""
echo "Done! The tray app is now running."
echo "Config file: $HOME/.config/balancetracker-tray/config.json"
echo ""
echo "To check status:  systemctl --user status balancetracker-tray"
echo "To view logs:     journalctl --user -u balancetracker-tray -f"
echo "To restart:       systemctl --user restart balancetracker-tray"
```

**Step 3: Make install.sh executable and commit**

```bash
chmod +x ~/Projects/Desktop_Mike/balancetracker-tray/install.sh
cd ~/Projects/Desktop_Mike
git add balancetracker-tray/balancetracker-tray.service balancetracker-tray/install.sh
git commit -m "feat(tray): add systemd service and install script"
```

---

### Task 15: End-to-end smoke test

**Step 1: Install system prerequisites if not already done**

```bash
sudo dnf install gnome-shell-extension-appindicator python3-gobject \
     python3-gobject-devel libayatana-appindicator-gtk3
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
```

**Step 2: Create config file**

```bash
mkdir -p ~/.config/balancetracker-tray
cat > ~/.config/balancetracker-tray/config.json <<'EOF'
{
  "bearer_token": "YOUR_GOOGLE_ID_TOKEN_HERE",
  "anthropic_api_key": "sk-ant-YOUR_KEY_HERE",
  "claude_model": "claude-haiku-4-5-20251001",
  "backend_url": "http://localhost:3000"
}
EOF
```

**Step 3: Run the app manually to verify it starts**

```bash
cd ~/Projects/Desktop_Mike/balancetracker-tray
.venv/bin/python3 app.py
```
Expected: tray icon appears in GNOME top bar; clicking it toggles the 480×600 translucent dark/green panel. Tasks, Notes, and Chat tabs load.

**Step 4: Run the install script**

```bash
~/Projects/Desktop_Mike/balancetracker-tray/install.sh
```
Expected: service enabled, starts on login automatically.

**Step 5: Run all unit tests one final time**

```bash
cd ~/Projects/Desktop_Mike/balancetracker-tray
python3 -m pytest tests/ -v
```
Expected: all tests pass.

**Step 6: Final commit**

```bash
cd ~/Projects/Desktop_Mike
git add -A
git commit -m "feat(tray): complete BalanceTracker tray app"
```
