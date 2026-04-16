# Phase 2 — Content Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Asset Library, Repurposing Pipeline (Whisper → PySceneDetect → FFmpeg → content atoms), Research Path (Tavily → Claude), Draft Generator, Approval Workflow, and Human Task system to the Social Content Factory backend + basic frontend pages.

**Architecture:** New Celery worker handles all heavy tasks (transcription, clip extraction, AI generation). API stays thin — it enqueues tasks and exposes CRUD for the new entities. Storage service abstraction (local in dev, S3 in prod) isolates file handling. Draft lifecycle follows a strict state machine enforced at the API layer.

**Tech Stack:** Celery + Redis, python-multipart, boto3, openai (Whisper), PySceneDetect, ffmpeg-python, opencv-python, tavily-python, anthropic (already present), Next.js 15 frontend.

---

## File Structure

### Backend — new files
- `backend/app/models/content.py` — SourceAsset, ContentAtom, Draft, DraftVersion, ApprovalRequest, HumanTask models
- `backend/app/worker.py` — Celery app instance
- `backend/app/services/storage.py` — StorageService abstraction (local + S3)
- `backend/app/tasks/__init__.py` — tasks package
- `backend/app/tasks/asset_tasks.py` — Celery tasks: transcription, scene detection, atom extraction
- `backend/app/tasks/draft_tasks.py` — Celery tasks: research path, draft generation
- `backend/app/api/v1/assets.py` — Asset Library API endpoints
- `backend/app/api/v1/drafts.py` — Draft CRUD + status transitions
- `backend/app/api/v1/approvals.py` — Approval workflow endpoints
- `backend/app/api/v1/human_tasks.py` — Human task endpoints
- `backend/tests/test_assets.py` — Asset API tests
- `backend/tests/test_drafts.py` — Draft API tests
- `backend/tests/test_approvals.py` — Approval workflow tests

### Backend — modified files
- `backend/requirements.txt` — add new dependencies
- `backend/app/config.py` — add openai_api_key, tavily_api_key, s3_*, redis_url, storage_backend
- `backend/app/models/brand.py` — add `assets` + `drafts` + `human_tasks` relationships
- `backend/app/api/v1/router.py` — register 4 new routers

### Frontend — new files
- `frontend/src/app/(dashboard)/assets/page.tsx` — Asset Library page
- `frontend/src/app/(dashboard)/drafts/page.tsx` — Drafts & Approval page
- `frontend/src/app/(dashboard)/tasks/page.tsx` — Human Tasks page
- `frontend/src/components/assets/AssetUpload.tsx` — drag-drop upload component
- `frontend/src/components/drafts/DraftCard.tsx` — draft card with approve/reject

### Frontend — modified files
- `frontend/src/types/api.ts` — add SourceAsset, ContentAtom, Draft, ApprovalRequest, HumanTask types
- `frontend/src/components/layout/Sidebar.tsx` — add Assets, Drafts, Tasks nav links

---

## Task 1: Dependencies + Config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Create: `backend/.env.example` (if not present)

- [ ] **Step 1: Update requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.36
alembic==1.13.3
psycopg2-binary==2.9.10
pydantic==2.9.2
pydantic-settings==2.6.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.2
anthropic==0.40.0
python-multipart==0.0.12
pytest==8.3.3
pytest-asyncio==0.24.0
celery[redis]==5.4.0
boto3==1.35.0
openai==1.51.0
scenedetect[opencv]==0.6.4
ffmpeg-python==0.2.0
tavily-python==0.5.0
```

- [ ] **Step 2: Update config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    anthropic_api_key: str
    openai_api_key: str = ""
    tavily_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"

    storage_backend: str = "local"  # "local" or "s3"
    storage_local_root: str = "/tmp/scf_uploads"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Install new packages in dev environment**

```bash
cd backend
pip install celery[redis]==5.4.0 boto3==1.35.0 openai==1.51.0 "scenedetect[opencv]==0.6.4" ffmpeg-python==0.2.0 tavily-python==0.5.0
```

Expected: No errors. `pip list` shows all packages.

- [ ] **Step 4: Verify config loads**

```bash
cd backend
python -c "from app.config import settings; print(settings.storage_backend)"
```

Expected: `local`

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "feat: add Phase 2 dependencies and config fields"
```

---

## Task 2: New Database Models

**Files:**
- Create: `backend/app/models/content.py`
- Modify: `backend/app/models/brand.py` (add relationships)

- [ ] **Step 1: Create content.py**

```python
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, JSON, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AssetType(str, enum.Enum):
    video = "video"
    audio = "audio"
    image = "image"
    text = "text"


class AssetStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class AtomType(str, enum.Enum):
    hook = "hook"
    key_point = "key_point"
    quote = "quote"
    cta = "cta"
    story = "story"
    clip = "clip"


class DraftStatus(str, enum.Enum):
    draft = "draft"
    needs_review = "needs_review"
    approved = "approved"
    rejected = "rejected"
    scheduled = "scheduled"
    publishing = "publishing"
    published = "published"
    failed = "failed"
    archived = "archived"


class HumanTaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class SourceAsset(Base):
    __tablename__ = "source_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus), default=AssetStatus.uploaded)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)  # S3 key or local path
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    transcription: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="assets")
    atoms: Mapped[list["ContentAtom"]] = relationship(back_populates="source_asset")
    drafts: Mapped[list["Draft"]] = relationship(back_populates="source_asset")


class ContentAtom(Base):
    __tablename__ = "content_atoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_asset_id: Mapped[int] = mapped_column(ForeignKey("source_assets.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    atom_type: Mapped[AtomType] = mapped_column(Enum(AtomType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    clip_start: Mapped[float] = mapped_column(nullable=True)   # seconds, for clips
    clip_end: Mapped[float] = mapped_column(nullable=True)     # seconds, for clips
    clip_key: Mapped[str] = mapped_column(String(1000), nullable=True)  # storage key for extracted clip
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source_asset: Mapped["SourceAsset"] = relationship(back_populates="atoms")


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    source_asset_id: Mapped[int] = mapped_column(ForeignKey("source_assets.id"), nullable=True)
    plan_item_id: Mapped[int] = mapped_column(ForeignKey("content_plan_items.id"), nullable=True)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(100), nullable=False)
    funnel_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[DraftStatus] = mapped_column(Enum(DraftStatus), default=DraftStatus.draft)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    media_keys: Mapped[list] = mapped_column(JSON, default=list)  # storage keys
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="drafts")
    source_asset: Mapped["SourceAsset"] = relationship(back_populates="drafts")
    versions: Mapped[list["DraftVersion"]] = relationship(back_populates="draft")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(back_populates="draft")


class DraftVersion(Base):
    __tablename__ = "draft_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    media_keys: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    draft: Mapped["Draft"] = relationship(back_populates="versions")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=True)  # approved / rejected / None
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    draft: Mapped["Draft"] = relationship(back_populates="approval_requests")


class HumanTask(Base):
    __tablename__ = "human_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=True)
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[HumanTaskStatus] = mapped_column(Enum(HumanTaskStatus), default=HumanTaskStatus.pending)
    result_asset_id: Mapped[int] = mapped_column(ForeignKey("source_assets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    brand: Mapped["Brand"] = relationship(back_populates="human_tasks")
```

- [ ] **Step 2: Add relationships to brand.py**

In `backend/app/models/brand.py`, add after existing relationships:

```python
    assets: Mapped[list["SourceAsset"]] = relationship(back_populates="brand")
    drafts: Mapped[list["Draft"]] = relationship(back_populates="brand")
    human_tasks: Mapped[list["HumanTask"]] = relationship(back_populates="brand")
```

Also add import at top of `brand.py` — not needed since relationships use strings.

- [ ] **Step 3: Register models so SQLAlchemy sees them**

In `backend/app/main.py` or `database.py`, ensure content models are imported before `create_all`. Add to the top-level imports in `main.py`:

```python
from app.models import content  # noqa: F401 — registers models
```

- [ ] **Step 4: Write failing test for model import**

```python
# backend/tests/test_models_content.py
def test_content_models_importable():
    from app.models.content import (
        SourceAsset, ContentAtom, Draft, DraftVersion,
        ApprovalRequest, HumanTask, DraftStatus, AssetStatus
    )
    assert DraftStatus.draft == "draft"
    assert AssetStatus.ready == "ready"
```

- [ ] **Step 5: Run test**

```bash
cd backend
pytest tests/test_models_content.py -v
```

Expected: PASS

- [ ] **Step 6: Verify tables create**

```bash
cd backend
python -c "
from app.database import Base, engine
from app.models import content  # noqa
Base.metadata.create_all(bind=engine)
print('tables ok')
"
```

Expected: `tables ok` (no errors)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/content.py backend/app/models/brand.py backend/app/main.py backend/tests/test_models_content.py
git commit -m "feat: add Phase 2 content models (SourceAsset, Draft, Approval, HumanTask)"
```

---

## Task 3: Celery Worker Setup

**Files:**
- Create: `backend/app/worker.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/docker-compose.worker.yml` (or extend existing)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_worker.py
def test_celery_app_importable():
    from app.worker import celery_app
    assert celery_app.main == "scf"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_worker.py -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Create worker.py**

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "scf",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.asset_tasks",
        "app.tasks.draft_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    task_track_started=True,
)
```

- [ ] **Step 4: Create tasks/__init__.py**

```python
# empty
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend
pytest tests/test_worker.py -v
```

Expected: PASS

- [ ] **Step 6: Verify worker starts (requires Redis running)**

```bash
cd backend
celery -A app.worker.celery_app inspect ping --timeout 2 2>&1 || echo "Redis not available (ok in CI)"
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/worker.py backend/app/tasks/__init__.py backend/tests/test_worker.py
git commit -m "feat: set up Celery worker app"
```

---

## Task 4: Storage Service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/storage.py`

The service abstracts file save/delete/presigned-url. In dev (local) it uses the filesystem. In prod it uses boto3 (S3-compatible).

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_storage.py
import os
import pytest
from unittest.mock import patch

@pytest.fixture
def local_storage(tmp_path):
    with patch("app.config.settings") as mock_settings:
        mock_settings.storage_backend = "local"
        mock_settings.storage_local_root = str(tmp_path)
        mock_settings.s3_bucket = ""
        mock_settings.s3_endpoint_url = ""
        mock_settings.s3_access_key = ""
        mock_settings.s3_secret_key = ""
        from app.services.storage import StorageService
        yield StorageService()

def test_local_save_and_read(local_storage, tmp_path):
    content = b"hello world"
    key = "test/file.txt"
    local_storage.save(key, content)
    assert local_storage.exists(key)

def test_local_delete(local_storage):
    content = b"data"
    key = "test/delete.txt"
    local_storage.save(key, content)
    local_storage.delete(key)
    assert not local_storage.exists(key)

def test_local_url(local_storage):
    key = "test/url.txt"
    local_storage.save(key, b"x")
    url = local_storage.url(key)
    assert key in url
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_storage.py -v
```

Expected: FAIL

- [ ] **Step 3: Create services/__init__.py**

```python
# empty
```

- [ ] **Step 4: Create services/storage.py**

```python
import os
import boto3
from app.config import settings


class StorageService:
    def __init__(self):
        self.backend = settings.storage_backend

        if self.backend == "s3":
            self._s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url or None,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            )
            self._bucket = settings.s3_bucket
        else:
            os.makedirs(settings.storage_local_root, exist_ok=True)
            self._root = settings.storage_local_root

    def save(self, key: str, data: bytes) -> None:
        if self.backend == "s3":
            self._s3.put_object(Bucket=self._bucket, Key=key, Body=data)
        else:
            path = os.path.join(self._root, key)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)

    def delete(self, key: str) -> None:
        if self.backend == "s3":
            self._s3.delete_object(Bucket=self._bucket, Key=key)
        else:
            path = os.path.join(self._root, key)
            if os.path.exists(path):
                os.remove(path)

    def exists(self, key: str) -> bool:
        if self.backend == "s3":
            try:
                self._s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except Exception:
                return False
        else:
            return os.path.exists(os.path.join(self._root, key))

    def url(self, key: str, expires: int = 3600) -> str:
        if self.backend == "s3":
            return self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
        else:
            return f"/files/{key}"

    def presigned_upload_url(self, key: str, expires: int = 3600) -> str:
        """Return a presigned PUT URL for direct upload (S3 only). Local returns /upload/{key}."""
        if self.backend == "s3":
            return self._s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
        return f"/api/v1/assets/upload-local/{key}"

    def read(self, key: str) -> bytes:
        if self.backend == "s3":
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            return obj["Body"].read()
        else:
            path = os.path.join(self._root, key)
            with open(path, "rb") as f:
                return f.read()


storage = StorageService()
```

- [ ] **Step 5: Run tests**

```bash
cd backend
pytest tests/test_storage.py -v
```

Expected: PASS (3 tests, local backend)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/storage.py backend/tests/test_storage.py
git commit -m "feat: add storage service abstraction (local + S3)"
```

---

## Task 5: Asset Library API

**Files:**
- Create: `backend/app/api/v1/assets.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_assets.py`

Endpoints:
- `POST /assets/initiate` — create SourceAsset record + return upload URL
- `POST /assets/{id}/confirm` — mark asset as uploaded, enqueue processing
- `GET /assets/` — list brand's assets
- `DELETE /assets/{id}` — delete asset

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_assets.py
import pytest
from unittest.mock import patch


def _register_and_login(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "password123", "name": "Test"
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "user@test.com", "password": "password123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_workspace_and_brand(client, headers):
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}, headers=headers)
    ws_id = ws.json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json={
        "name": "Brand", "company_type": "product",
        "description": "desc", "target_audience": "all",
        "goals": [], "tone_of_voice": "friendly",
        "posting_frequency": "daily", "networks": []
    }, headers=headers)
    brand = client.get(f"/api/v1/workspaces/{ws_id}/brand", headers=headers).json()
    return ws_id, brand["id"]


def test_initiate_upload(client):
    headers = _register_and_login(client)
    ws_id, brand_id = _create_workspace_and_brand(client, headers)
    resp = client.post("/api/v1/assets/initiate", json={
        "brand_id": brand_id,
        "name": "interview.mp4",
        "asset_type": "video",
        "file_size": 1024 * 1024 * 100,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "asset_id" in data
    assert "upload_url" in data


def test_list_assets(client):
    headers = _register_and_login(client)
    ws_id, brand_id = _create_workspace_and_brand(client, headers)
    client.post("/api/v1/assets/initiate", json={
        "brand_id": brand_id, "name": "file.mp4",
        "asset_type": "video", "file_size": 1000,
    }, headers=headers)
    resp = client.get(f"/api/v1/assets/?brand_id={brand_id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_confirm_asset(client):
    headers = _register_and_login(client)
    ws_id, brand_id = _create_workspace_and_brand(client, headers)
    init = client.post("/api/v1/assets/initiate", json={
        "brand_id": brand_id, "name": "file.mp4",
        "asset_type": "video", "file_size": 1000,
    }, headers=headers)
    asset_id = init.json()["asset_id"]

    with patch("app.tasks.asset_tasks.process_asset.delay") as mock_task:
        resp = client.post(f"/api/v1/assets/{asset_id}/confirm", headers=headers)
        assert resp.status_code == 200
        mock_task.assert_called_once_with(asset_id)


def test_delete_asset(client):
    headers = _register_and_login(client)
    ws_id, brand_id = _create_workspace_and_brand(client, headers)
    init = client.post("/api/v1/assets/initiate", json={
        "brand_id": brand_id, "name": "file.mp4",
        "asset_type": "video", "file_size": 1000,
    }, headers=headers)
    asset_id = init.json()["asset_id"]
    resp = client.delete(f"/api/v1/assets/{asset_id}", headers=headers)
    assert resp.status_code == 204
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_assets.py -v
```

Expected: FAIL (404 on asset routes)

- [ ] **Step 3: Create assets.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import SourceAsset, AssetStatus, AssetType
from app.services.storage import storage

router = APIRouter(prefix="/assets", tags=["assets"])


class InitiateUploadRequest(BaseModel):
    brand_id: int
    name: str
    asset_type: AssetType
    file_size: Optional[int] = None
    tags: list[str] = []


class InitiateUploadResponse(BaseModel):
    asset_id: int
    upload_url: str
    storage_key: str


class AssetOut(BaseModel):
    id: int
    brand_id: int
    name: str
    asset_type: str
    status: str
    storage_key: str
    file_size: Optional[int]
    duration_seconds: Optional[int]
    transcription: Optional[str]
    tags: list

    class Config:
        from_attributes = True


@router.post("/initiate", response_model=InitiateUploadResponse)
def initiate_upload(
    body: InitiateUploadRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    import uuid
    storage_key = f"brands/{body.brand_id}/assets/{uuid.uuid4()}/{body.name}"
    asset = SourceAsset(
        brand_id=body.brand_id,
        name=body.name,
        asset_type=body.asset_type,
        status=AssetStatus.uploaded,
        storage_key=storage_key,
        file_size=body.file_size,
        tags=body.tags,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    upload_url = storage.presigned_upload_url(storage_key)
    return InitiateUploadResponse(
        asset_id=asset.id,
        upload_url=upload_url,
        storage_key=storage_key,
    )


@router.post("/{asset_id}/confirm")
def confirm_upload(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = db.get(SourceAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.status = AssetStatus.processing
    db.commit()

    from app.tasks.asset_tasks import process_asset
    process_asset.delay(asset_id)

    return {"status": "processing", "asset_id": asset_id}


@router.get("/", response_model=list[AssetOut])
def list_assets(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(SourceAsset).filter(SourceAsset.brand_id == brand_id).all()


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = db.get(SourceAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        storage.delete(asset.storage_key)
    except Exception:
        pass
    db.delete(asset)
    db.commit()
```

- [ ] **Step 4: Create stub asset_tasks.py** (real implementation in Task 6)

```python
# backend/app/tasks/asset_tasks.py
from app.worker import celery_app


@celery_app.task(name="process_asset")
def process_asset(asset_id: int):
    """Transcribe + scene detect + extract atoms. Implemented in Task 6."""
    pass
```

- [ ] **Step 5: Register router**

In `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter
from app.api.v1 import auth, workspaces, brands, strategy, assets

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(brands.router, tags=["brands"])
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
router.include_router(assets.router)
```

- [ ] **Step 6: Run tests**

```bash
cd backend
pytest tests/test_assets.py -v
```

Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/assets.py backend/app/api/v1/router.py backend/app/tasks/asset_tasks.py backend/tests/test_assets.py
git commit -m "feat: add Asset Library API (initiate, confirm, list, delete)"
```

---

## Task 6: Repurposing Pipeline (Whisper + PySceneDetect + Claude atoms)

**Files:**
- Modify: `backend/app/tasks/asset_tasks.py`

The `process_asset` task:
1. Reads file from storage
2. Runs Whisper transcription (if video/audio)
3. Runs PySceneDetect + FFmpeg clip extraction (if video)
4. Calls Claude to extract content atoms from transcription
5. Saves atoms to DB, updates asset status to ready

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_asset_tasks.py
import pytest
from unittest.mock import patch, MagicMock


def test_process_asset_runs(db):
    from app.models.content import SourceAsset, AssetType, AssetStatus
    asset = SourceAsset(
        brand_id=1,
        name="test.mp4",
        asset_type=AssetType.video,
        status=AssetStatus.processing,
        storage_key="brands/1/assets/test.mp4",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    with patch("app.tasks.asset_tasks.storage.read", return_value=b"fake_video_data"), \
         patch("app.tasks.asset_tasks._transcribe", return_value="Hello world this is a test"), \
         patch("app.tasks.asset_tasks._detect_scenes", return_value=[]), \
         patch("app.tasks.asset_tasks._extract_atoms", return_value=[
             {"type": "hook", "content": "Hello world"},
             {"type": "key_point", "content": "This is a test"},
         ]):
        from app.tasks.asset_tasks import _process_asset_sync
        _process_asset_sync(asset.id, db)

    db.refresh(asset)
    assert asset.status == AssetStatus.ready
    assert asset.transcription == "Hello world this is a test"

    from app.models.content import ContentAtom
    atoms = db.query(ContentAtom).filter(ContentAtom.source_asset_id == asset.id).all()
    assert len(atoms) == 2
    assert atoms[0].atom_type == "hook"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_asset_tasks.py -v
```

Expected: FAIL (no `_process_asset_sync`)

- [ ] **Step 3: Implement asset_tasks.py**

```python
# backend/app/tasks/asset_tasks.py
import os
import tempfile
from app.worker import celery_app
from app.config import settings


def _transcribe(audio_path: str) -> str:
    """Call OpenAI Whisper API on local file. Returns transcript text."""
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ru",
        )
    return result.text


def _detect_scenes(video_path: str) -> list[dict]:
    """Detect scene changes. Returns list of {start, end} in seconds."""
    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector
    except ImportError:
        return []

    video = open_video(video_path)
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=27.0))
    manager.detect_scenes(video)
    scene_list = manager.get_scene_list()
    return [
        {"start": s[0].get_seconds(), "end": s[1].get_seconds()}
        for s in scene_list
    ]


def _extract_clip(video_path: str, start: float, end: float, out_path: str) -> None:
    """Use ffmpeg-python to extract clip."""
    import ffmpeg
    (
        ffmpeg
        .input(video_path, ss=start, to=end)
        .output(out_path, c="copy")
        .overwrite_output()
        .run(quiet=True)
    )


def _extract_atoms(transcription: str, brand_id: int) -> list[dict]:
    """Call Claude to extract content atoms from transcription."""
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""Extract content atoms from this transcription for social media reuse.
Return a JSON array of objects with fields: type (hook/key_point/quote/cta/story) and content.
Extract 5-10 atoms. Transcription:

{transcription}

Return only valid JSON array, no other text."""
    import json
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    return json.loads(text)


def _process_asset_sync(asset_id: int, db):
    from app.models.content import SourceAsset, ContentAtom, AssetStatus, AtomType
    from app.services.storage import storage

    asset = db.get(SourceAsset, asset_id)
    if not asset:
        return

    try:
        raw = storage.read(asset.storage_key)
        suffix = os.path.splitext(asset.name)[1] or ".mp4"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        transcription = ""
        scenes = []

        if asset.asset_type in ("video", "audio"):
            transcription = _transcribe(tmp_path)
            asset.transcription = transcription

        if asset.asset_type == "video":
            scenes = _detect_scenes(tmp_path)
            # Save clips
            for i, scene in enumerate(scenes[:10]):  # limit to 10 clips
                clip_key = f"{asset.storage_key}_clip_{i}.mp4"
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as clip_tmp:
                    _extract_clip(tmp_path, scene["start"], scene["end"], clip_tmp.name)
                    with open(clip_tmp.name, "rb") as f:
                        storage.save(clip_key, f.read())
                    os.unlink(clip_tmp.name)

                atom = ContentAtom(
                    source_asset_id=asset.id,
                    brand_id=asset.brand_id,
                    atom_type=AtomType.clip,
                    content=f"Clip {i+1}: {scene['start']:.1f}s–{scene['end']:.1f}s",
                    clip_start=scene["start"],
                    clip_end=scene["end"],
                    clip_key=clip_key,
                )
                db.add(atom)

        if transcription:
            atoms_data = _extract_atoms(transcription, asset.brand_id)
            for a in atoms_data:
                try:
                    atype = AtomType(a["type"])
                except ValueError:
                    atype = AtomType.key_point
                atom = ContentAtom(
                    source_asset_id=asset.id,
                    brand_id=asset.brand_id,
                    atom_type=atype,
                    content=a["content"],
                )
                db.add(atom)

        os.unlink(tmp_path)
        asset.status = AssetStatus.ready

    except Exception as e:
        asset.status = AssetStatus.failed
        asset.meta = {"error": str(e)}

    db.commit()


@celery_app.task(name="process_asset")
def process_asset(asset_id: int):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        _process_asset_sync(asset_id, db)
    finally:
        db.close()
```

- [ ] **Step 4: Run test**

```bash
cd backend
pytest tests/test_asset_tasks.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/asset_tasks.py backend/tests/test_asset_tasks.py
git commit -m "feat: implement repurposing pipeline (Whisper + PySceneDetect + FFmpeg + Claude atoms)"
```

---

## Task 7: Draft API

**Files:**
- Create: `backend/app/api/v1/drafts.py`
- Create: `backend/app/tasks/draft_tasks.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_drafts.py`

Endpoints:
- `POST /drafts/generate` — enqueue Claude draft generation from atoms or research
- `GET /drafts/` — list drafts for a brand
- `GET /drafts/{id}` — get draft with versions
- `PATCH /drafts/{id}` — update text (creates new DraftVersion)
- `POST /drafts/{id}/submit` — set status to needs_review
- `DELETE /drafts/{id}` — archive

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_drafts.py
import pytest
from unittest.mock import patch


def _auth_and_setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "u@t.com", "password": "pass1234", "name": "U"
    })
    resp = client.post("/api/v1/auth/login", json={"email": "u@t.com", "password": "pass1234"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}, headers=headers)
    ws_id = ws.json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json={
        "name": "B", "company_type": "product",
        "description": "d", "target_audience": "a",
        "goals": [], "tone_of_voice": "f",
        "posting_frequency": "daily", "networks": []
    }, headers=headers)
    brand = client.get(f"/api/v1/workspaces/{ws_id}/brand", headers=headers).json()
    return headers, ws_id, brand["id"]


def test_generate_draft(client):
    headers, ws_id, brand_id = _auth_and_setup(client)
    with patch("app.tasks.draft_tasks.generate_draft.delay") as mock:
        resp = client.post("/api/v1/drafts/generate", json={
            "brand_id": brand_id,
            "network": "instagram",
            "format": "carousel",
            "funnel_stage": "tofu",
        }, headers=headers)
        assert resp.status_code == 202
        assert mock.called


def test_list_drafts(client):
    headers, ws_id, brand_id = _auth_and_setup(client)
    resp = client.get(f"/api/v1/drafts/?brand_id={brand_id}", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_update_draft_creates_version(client, db):
    from app.models.content import Draft, DraftStatus
    headers, ws_id, brand_id = _auth_and_setup(client)
    draft = Draft(
        brand_id=brand_id,
        network="instagram",
        format="carousel",
        funnel_stage="tofu",
        status=DraftStatus.draft,
        text="Original text",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.patch(f"/api/v1/drafts/{draft.id}", json={"text": "Updated text"}, headers=headers)
    assert resp.status_code == 200

    from app.models.content import DraftVersion
    versions = db.query(DraftVersion).filter(DraftVersion.draft_id == draft.id).all()
    assert len(versions) == 1
    assert versions[0].text == "Original text"


def test_submit_draft(client, db):
    from app.models.content import Draft, DraftStatus
    headers, ws_id, brand_id = _auth_and_setup(client)
    draft = Draft(
        brand_id=brand_id,
        network="telegram",
        format="longread",
        funnel_stage="mofu",
        status=DraftStatus.draft,
        text="Some text",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.post(f"/api/v1/drafts/{draft.id}/submit", headers=headers)
    assert resp.status_code == 200
    db.refresh(draft)
    assert draft.status == DraftStatus.needs_review
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_drafts.py -v
```

Expected: FAIL

- [ ] **Step 3: Create stub draft_tasks.py**

```python
# backend/app/tasks/draft_tasks.py
from app.worker import celery_app


@celery_app.task(name="generate_draft")
def generate_draft(brand_id: int, network: str, format: str, funnel_stage: str,
                   source_asset_id: int = None, draft_id: int = None):
    """Research path or repurposing path draft generation. Implemented fully in Task 8."""
    pass
```

- [ ] **Step 4: Create drafts.py**

```python
# backend/app/api/v1/drafts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import Draft, DraftVersion, DraftStatus

router = APIRouter(prefix="/drafts", tags=["drafts"])


class GenerateRequest(BaseModel):
    brand_id: int
    network: str
    format: str
    funnel_stage: str
    source_asset_id: Optional[int] = None


class DraftUpdateRequest(BaseModel):
    text: Optional[str] = None
    hashtags: Optional[list[str]] = None


class DraftOut(BaseModel):
    id: int
    brand_id: int
    network: str
    format: str
    funnel_stage: str
    status: str
    text: Optional[str]
    hashtags: list
    media_keys: list

    class Config:
        from_attributes = True


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_draft(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.tasks.draft_tasks import generate_draft as task
    task.delay(
        brand_id=body.brand_id,
        network=body.network,
        format=body.format,
        funnel_stage=body.funnel_stage,
        source_asset_id=body.source_asset_id,
    )
    return {"status": "queued"}


@router.get("/", response_model=list[DraftOut])
def list_drafts(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(Draft).filter(Draft.brand_id == brand_id).all()


@router.get("/{draft_id}", response_model=DraftOut)
def get_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/{draft_id}", response_model=DraftOut)
def update_draft(
    draft_id: int,
    body: DraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status not in (DraftStatus.draft, DraftStatus.rejected):
        raise HTTPException(status_code=400, detail="Can only edit drafts in draft/rejected status")

    # Save version before modifying
    version_count = db.query(DraftVersion).filter(DraftVersion.draft_id == draft_id).count()
    version = DraftVersion(
        draft_id=draft_id,
        version=version_count + 1,
        text=draft.text,
        media_keys=draft.media_keys,
    )
    db.add(version)

    if body.text is not None:
        draft.text = body.text
    if body.hashtags is not None:
        draft.hashtags = body.hashtags
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{draft_id}/submit", response_model=DraftOut)
def submit_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status not in (DraftStatus.draft, DraftStatus.rejected):
        raise HTTPException(status_code=400, detail="Can only submit draft/rejected drafts")
    draft.status = DraftStatus.needs_review
    db.commit()
    db.refresh(draft)
    return draft


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = DraftStatus.archived
    db.commit()
```

- [ ] **Step 5: Register drafts router in router.py**

```python
from fastapi import APIRouter
from app.api.v1 import auth, workspaces, brands, strategy, assets, drafts

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(brands.router, tags=["brands"])
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
router.include_router(assets.router)
router.include_router(drafts.router)
```

- [ ] **Step 6: Run tests**

```bash
cd backend
pytest tests/test_drafts.py -v
```

Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/drafts.py backend/app/api/v1/router.py backend/app/tasks/draft_tasks.py backend/tests/test_drafts.py
git commit -m "feat: add Draft API (generate, list, update, submit, delete)"
```

---

## Task 8: Research Path + Draft Generation Task

**Files:**
- Modify: `backend/app/tasks/draft_tasks.py`
- Create: `backend/tests/test_draft_tasks.py`

The `generate_draft` task:
- If `source_asset_id` → repurposing path: picks atoms, generates per-network text with Claude
- If no asset → research path: Tavily search → Claude generates text
- Creates Draft record with status=draft

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_draft_tasks.py
import pytest
from unittest.mock import patch, MagicMock


def test_generate_draft_research_path(db):
    from app.models.brand import Brand
    brand = Brand(
        workspace_id=1,
        name="Test Brand",
        company_type="product",
        description="A great product",
        target_audience="SMB owners",
        goals=[],
        tone_of_voice="friendly",
        posting_frequency="daily",
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)

    mock_tavily = MagicMock()
    mock_tavily.search.return_value = {
        "results": [{"content": "Trending topic about AI tools for SMB"}]
    }
    mock_claude_msg = MagicMock()
    mock_claude_msg.content = [MagicMock(text="Post text about AI for SMB owners #smb #ai")]

    with patch("app.tasks.draft_tasks.TavilyClient", return_value=mock_tavily), \
         patch("app.tasks.draft_tasks.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_msg

        from app.tasks.draft_tasks import _generate_draft_sync
        _generate_draft_sync(
            brand_id=brand.id,
            network="instagram",
            format="carousel",
            funnel_stage="tofu",
            source_asset_id=None,
            db=db,
        )

    from app.models.content import Draft, DraftStatus
    drafts = db.query(Draft).filter(Draft.brand_id == brand.id).all()
    assert len(drafts) == 1
    assert drafts[0].status == DraftStatus.draft
    assert "AI" in drafts[0].text or len(drafts[0].text) > 5


def test_generate_draft_repurposing_path(db):
    from app.models.brand import Brand
    from app.models.content import SourceAsset, ContentAtom, AssetType, AssetStatus, AtomType
    brand = Brand(
        workspace_id=1,
        name="B2",
        company_type="service",
        description="desc",
        target_audience="ta",
        goals=[],
        tone_of_voice="professional",
        posting_frequency="weekly",
    )
    db.add(brand)
    db.commit()

    asset = SourceAsset(
        brand_id=brand.id, name="video.mp4",
        asset_type=AssetType.video, status=AssetStatus.ready,
        storage_key="brands/1/video.mp4",
        transcription="Great product launch event",
    )
    db.add(asset)
    db.commit()

    atom = ContentAtom(
        source_asset_id=asset.id, brand_id=brand.id,
        atom_type=AtomType.hook,
        content="Great product launch happening right now!",
    )
    db.add(atom)
    db.commit()

    mock_claude_msg = MagicMock()
    mock_claude_msg.content = [MagicMock(text="Amazing launch carousel text! #launch #product")]

    with patch("app.tasks.draft_tasks.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_msg

        from app.tasks.draft_tasks import _generate_draft_sync
        _generate_draft_sync(
            brand_id=brand.id,
            network="vk",
            format="long_post",
            funnel_stage="mofu",
            source_asset_id=asset.id,
            db=db,
        )

    from app.models.content import Draft
    drafts = db.query(Draft).filter(Draft.brand_id == brand.id).all()
    assert len(drafts) == 1
    assert "launch" in drafts[0].text.lower() or len(drafts[0].text) > 5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_draft_tasks.py -v
```

Expected: FAIL (no `_generate_draft_sync`)

- [ ] **Step 3: Implement draft_tasks.py**

```python
# backend/app/tasks/draft_tasks.py
from app.worker import celery_app
from app.config import settings


def _research_context(topic: str, brand_description: str) -> str:
    """Fetch relevant context via Tavily search."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        results = client.search(
            query=f"{topic} {brand_description}",
            search_depth="basic",
            max_results=3,
        )
        snippets = [r["content"] for r in results.get("results", [])]
        return "\n".join(snippets)
    except Exception:
        return ""


def _build_research_prompt(brand, network: str, format: str, funnel_stage: str, context: str) -> str:
    return f"""You are a social media content writer for a brand.

Brand: {brand.name}
Description: {brand.description}
Target audience: {brand.target_audience}
Tone of voice: {brand.tone_of_voice}
Network: {network}
Format: {format}
Funnel stage: {funnel_stage} (tofu=awareness, mofu=consideration, bofu=conversion, retention=loyalty)

Relevant context from web research:
{context}

Write one post for {network} in {format} format. Match tone of voice. Include relevant hashtags.
Write in Russian. Return only the post text, no explanations."""


def _build_repurposing_prompt(brand, network: str, format: str, funnel_stage: str, atoms: list) -> str:
    atom_texts = "\n".join([f"- [{a.atom_type}]: {a.content}" for a in atoms])
    return f"""You are a social media content writer repurposing source material.

Brand: {brand.name}
Description: {brand.description}
Target audience: {brand.target_audience}
Tone of voice: {brand.tone_of_voice}
Network: {network}
Format: {format}
Funnel stage: {funnel_stage}

Content atoms extracted from source video/audio:
{atom_texts}

Using the atoms above, write one post for {network} in {format} format.
Match tone of voice. Include hashtags. Write in Russian.
Return only the post text."""


def _call_claude(prompt: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _generate_draft_sync(brand_id: int, network: str, format: str, funnel_stage: str,
                          source_asset_id, db):
    from app.models.brand import Brand
    from app.models.content import ContentAtom, Draft, DraftStatus, SourceAsset

    brand = db.get(Brand, brand_id)
    if not brand:
        return

    if source_asset_id:
        # Repurposing path
        atoms = db.query(ContentAtom).filter(
            ContentAtom.source_asset_id == source_asset_id
        ).limit(10).all()
        prompt = _build_repurposing_prompt(brand, network, format, funnel_stage, atoms)
    else:
        # Research path
        topic = f"{brand.description} {funnel_stage} content for {network}"
        context = _research_context(topic, brand.description)
        prompt = _build_research_prompt(brand, network, format, funnel_stage, context)

    text = _call_claude(prompt)

    draft = Draft(
        brand_id=brand_id,
        source_asset_id=source_asset_id,
        network=network,
        format=format,
        funnel_stage=funnel_stage,
        status=DraftStatus.draft,
        text=text,
    )
    db.add(draft)
    db.commit()


@celery_app.task(name="generate_draft")
def generate_draft(brand_id: int, network: str, format: str, funnel_stage: str,
                   source_asset_id=None, draft_id=None):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        _generate_draft_sync(brand_id, network, format, funnel_stage, source_asset_id, db)
    finally:
        db.close()
```

- [ ] **Step 4: Run tests**

```bash
cd backend
pytest tests/test_draft_tasks.py -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Run all tests to verify no regressions**

```bash
cd backend
pytest -v
```

Expected: All passing

- [ ] **Step 6: Commit**

```bash
git add backend/app/tasks/draft_tasks.py backend/tests/test_draft_tasks.py
git commit -m "feat: implement research path and repurposing path draft generation"
```

---

## Task 9: Approval Workflow API

**Files:**
- Create: `backend/app/api/v1/approvals.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_approvals.py`

Endpoints:
- `GET /approvals/queue?brand_id=X` — list drafts in needs_review status
- `POST /approvals/{draft_id}/approve` — approve, set draft status=approved
- `POST /approvals/{draft_id}/reject` — reject with comment, set status=rejected

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_approvals.py
import pytest


def _auth_and_brand(client):
    client.post("/api/v1/auth/register", json={"email": "a@t.com", "password": "pass1234", "name": "A"})
    resp = client.post("/api/v1/auth/login", json={"email": "a@t.com", "password": "pass1234"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}, headers=headers)
    ws_id = ws.json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json={
        "name": "B", "company_type": "product",
        "description": "d", "target_audience": "a",
        "goals": [], "tone_of_voice": "f",
        "posting_frequency": "daily", "networks": []
    }, headers=headers)
    brand = client.get(f"/api/v1/workspaces/{ws_id}/brand", headers=headers).json()
    return headers, brand["id"]


def test_approval_queue_empty(client):
    headers, brand_id = _auth_and_brand(client)
    resp = client.get(f"/api/v1/approvals/queue?brand_id={brand_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_approve_draft(client, db):
    from app.models.content import Draft, DraftStatus
    headers, brand_id = _auth_and_brand(client)
    draft = Draft(
        brand_id=brand_id, network="telegram",
        format="longread", funnel_stage="mofu",
        status=DraftStatus.needs_review, text="Review me",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.post(f"/api/v1/approvals/{draft.id}/approve",
                       json={"comment": "Looks great"}, headers=headers)
    assert resp.status_code == 200
    db.refresh(draft)
    assert draft.status == DraftStatus.approved


def test_reject_draft(client, db):
    from app.models.content import Draft, DraftStatus
    headers, brand_id = _auth_and_brand(client)
    draft = Draft(
        brand_id=brand_id, network="vk",
        format="long_post", funnel_stage="bofu",
        status=DraftStatus.needs_review, text="Draft text",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.post(f"/api/v1/approvals/{draft.id}/reject",
                       json={"comment": "Wrong tone"}, headers=headers)
    assert resp.status_code == 200
    db.refresh(draft)
    assert draft.status == DraftStatus.rejected


def test_cannot_approve_non_review_draft(client, db):
    from app.models.content import Draft, DraftStatus
    headers, brand_id = _auth_and_brand(client)
    draft = Draft(
        brand_id=brand_id, network="instagram",
        format="carousel", funnel_stage="tofu",
        status=DraftStatus.draft, text="Not submitted",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.post(f"/api/v1/approvals/{draft.id}/approve",
                       json={}, headers=headers)
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_approvals.py -v
```

Expected: FAIL

- [ ] **Step 3: Create approvals.py**

```python
# backend/app/api/v1/approvals.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import Draft, DraftStatus, ApprovalRequest

router = APIRouter(prefix="/approvals", tags=["approvals"])


class DecisionRequest(BaseModel):
    comment: Optional[str] = None


class DraftOut(BaseModel):
    id: int
    brand_id: int
    network: str
    format: str
    funnel_stage: str
    status: str
    text: Optional[str]

    class Config:
        from_attributes = True


@router.get("/queue", response_model=list[DraftOut])
def approval_queue(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(Draft).filter(
        Draft.brand_id == brand_id,
        Draft.status == DraftStatus.needs_review,
    ).all()


@router.post("/{draft_id}/approve", response_model=DraftOut)
def approve_draft(
    draft_id: int,
    body: DecisionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.needs_review:
        raise HTTPException(status_code=400, detail="Draft is not in needs_review status")

    ar = ApprovalRequest(
        draft_id=draft_id,
        reviewer_id=current_user.id,
        decision="approved",
        comment=body.comment,
        decided_at=datetime.utcnow(),
    )
    db.add(ar)
    draft.status = DraftStatus.approved
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{draft_id}/reject", response_model=DraftOut)
def reject_draft(
    draft_id: int,
    body: DecisionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.needs_review:
        raise HTTPException(status_code=400, detail="Draft is not in needs_review status")

    ar = ApprovalRequest(
        draft_id=draft_id,
        reviewer_id=current_user.id,
        decision="rejected",
        comment=body.comment,
        decided_at=datetime.utcnow(),
    )
    db.add(ar)
    draft.status = DraftStatus.rejected
    db.commit()
    db.refresh(draft)
    return draft
```

- [ ] **Step 4: Register approvals router**

In `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter
from app.api.v1 import auth, workspaces, brands, strategy, assets, drafts, approvals

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(brands.router, tags=["brands"])
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
router.include_router(assets.router)
router.include_router(drafts.router)
router.include_router(approvals.router)
```

- [ ] **Step 5: Run tests**

```bash
cd backend
pytest tests/test_approvals.py -v
```

Expected: 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/approvals.py backend/app/api/v1/router.py backend/tests/test_approvals.py
git commit -m "feat: add approval workflow API (queue, approve, reject)"
```

---

## Task 10: Human Task System API

**Files:**
- Create: `backend/app/api/v1/human_tasks.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_human_tasks.py`

Endpoints:
- `POST /human-tasks/` — create task
- `GET /human-tasks/?brand_id=X` — list tasks
- `PATCH /human-tasks/{id}/complete` — mark complete + attach result_asset_id

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_human_tasks.py


def _auth_and_brand(client):
    client.post("/api/v1/auth/register", json={"email": "ht@t.com", "password": "pass1234", "name": "HT"})
    resp = client.post("/api/v1/auth/login", json={"email": "ht@t.com", "password": "pass1234"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}, headers=headers)
    ws_id = ws.json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json={
        "name": "B", "company_type": "product",
        "description": "d", "target_audience": "a",
        "goals": [], "tone_of_voice": "f",
        "posting_frequency": "daily", "networks": []
    }, headers=headers)
    brand = client.get(f"/api/v1/workspaces/{ws_id}/brand", headers=headers).json()
    return headers, brand["id"]


def test_create_human_task(client):
    headers, brand_id = _auth_and_brand(client)
    resp = client.post("/api/v1/human-tasks/", json={
        "brand_id": brand_id,
        "title": "Record intro video",
        "description": "Record a 30-second intro for the new product launch",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Record intro video"
    assert data["status"] == "pending"


def test_list_human_tasks(client):
    headers, brand_id = _auth_and_brand(client)
    client.post("/api/v1/human-tasks/", json={
        "brand_id": brand_id, "title": "Task 1",
    }, headers=headers)
    resp = client.get(f"/api/v1/human-tasks/?brand_id={brand_id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_complete_human_task(client, db):
    from app.models.content import HumanTask, HumanTaskStatus
    headers, brand_id = _auth_and_brand(client)
    task = HumanTask(brand_id=brand_id, title="Record video")
    db.add(task)
    db.commit()
    db.refresh(task)

    resp = client.patch(f"/api/v1/human-tasks/{task.id}/complete",
                        json={}, headers=headers)
    assert resp.status_code == 200
    db.refresh(task)
    assert task.status == HumanTaskStatus.completed
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_human_tasks.py -v
```

Expected: FAIL

- [ ] **Step 3: Create human_tasks.py**

```python
# backend/app/api/v1/human_tasks.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import HumanTask, HumanTaskStatus

router = APIRouter(prefix="/human-tasks", tags=["human-tasks"])


class HumanTaskCreate(BaseModel):
    brand_id: int
    title: str
    description: Optional[str] = None
    draft_id: Optional[int] = None


class HumanTaskComplete(BaseModel):
    result_asset_id: Optional[int] = None


class HumanTaskOut(BaseModel):
    id: int
    brand_id: int
    title: str
    description: Optional[str]
    status: str
    result_asset_id: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.post("/", response_model=HumanTaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    body: HumanTaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = HumanTask(
        brand_id=body.brand_id,
        draft_id=body.draft_id,
        title=body.title,
        description=body.description,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/", response_model=list[HumanTaskOut])
def list_tasks(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(HumanTask).filter(HumanTask.brand_id == brand_id).all()


@router.patch("/{task_id}/complete", response_model=HumanTaskOut)
def complete_task(
    task_id: int,
    body: HumanTaskComplete,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.get(HumanTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = HumanTaskStatus.completed
    task.completed_at = datetime.utcnow()
    if body.result_asset_id:
        task.result_asset_id = body.result_asset_id
    db.commit()
    db.refresh(task)
    return task
```

- [ ] **Step 4: Register in router.py**

```python
from fastapi import APIRouter
from app.api.v1 import auth, workspaces, brands, strategy, assets, drafts, approvals, human_tasks

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(brands.router, tags=["brands"])
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
router.include_router(assets.router)
router.include_router(drafts.router)
router.include_router(approvals.router)
router.include_router(human_tasks.router)
```

- [ ] **Step 5: Run tests**

```bash
cd backend
pytest tests/test_human_tasks.py -v
```

Expected: 3 tests PASS

- [ ] **Step 6: Run full test suite**

```bash
cd backend
pytest -v
```

Expected: All tests PASS (15+ tests from Phase 1 + new ones)

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/human_tasks.py backend/app/api/v1/router.py backend/tests/test_human_tasks.py
git commit -m "feat: add Human Task system API (create, list, complete)"
```

---

## Task 11: Frontend Types + API Client

**Files:**
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Add Phase 2 types to api.ts**

Read the current api.ts and add at the bottom:

```typescript
// Phase 2 types

export interface SourceAsset {
  id: number;
  brand_id: number;
  name: string;
  asset_type: "video" | "audio" | "image" | "text";
  status: "uploaded" | "processing" | "ready" | "failed";
  storage_key: string;
  file_size: number | null;
  duration_seconds: number | null;
  transcription: string | null;
  tags: string[];
}

export interface ContentAtom {
  id: number;
  source_asset_id: number;
  atom_type: "hook" | "key_point" | "quote" | "cta" | "story" | "clip";
  content: string;
  clip_start: number | null;
  clip_end: number | null;
  clip_key: string | null;
}

export type DraftStatus =
  | "draft"
  | "needs_review"
  | "approved"
  | "rejected"
  | "scheduled"
  | "publishing"
  | "published"
  | "failed"
  | "archived";

export interface Draft {
  id: number;
  brand_id: number;
  network: string;
  format: string;
  funnel_stage: string;
  status: DraftStatus;
  text: string | null;
  hashtags: string[];
  media_keys: string[];
  source_asset_id: number | null;
}

export interface HumanTask {
  id: number;
  brand_id: number;
  title: string;
  description: string | null;
  status: "pending" | "in_progress" | "completed" | "cancelled";
  result_asset_id: number | null;
  created_at: string;
  completed_at: string | null;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat: add Phase 2 API types (SourceAsset, Draft, HumanTask)"
```

---

## Task 12: Frontend — Asset Library Page

**Files:**
- Create: `frontend/src/app/(dashboard)/assets/page.tsx`
- Create: `frontend/src/components/assets/AssetUpload.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx` (add Assets link)

- [ ] **Step 1: Create AssetUpload.tsx**

```tsx
"use client";
import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { SourceAsset } from "@/types/api";

interface Props {
  brandId: number;
  onUploaded: (asset: SourceAsset) => void;
}

export function AssetUpload({ brandId, onUploaded }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setUploading(true);
    setError("");
    try {
      const assetType = file.type.startsWith("video")
        ? "video"
        : file.type.startsWith("audio")
        ? "audio"
        : file.type.startsWith("image")
        ? "image"
        : "text";

      const initRes = await api.post("/assets/initiate", {
        brand_id: brandId,
        name: file.name,
        asset_type: assetType,
        file_size: file.size,
      });
      const { asset_id, upload_url } = initRes.data;

      // Upload file to storage (local dev: skip, S3: PUT to presigned URL)
      if (!upload_url.startsWith("/api/v1/assets/upload-local")) {
        await fetch(upload_url, { method: "PUT", body: file });
      }

      const confirmRes = await api.post(`/assets/${asset_id}/confirm`);
      onUploaded({ ...confirmRes.data, id: asset_id, name: file.name });
    } catch {
      setError("Ошибка загрузки файла");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center cursor-pointer hover:border-sky-500 transition-colors"
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept="video/*,audio/*,image/*"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      {uploading ? (
        <p className="text-slate-400">Загружаем...</p>
      ) : (
        <>
          <p className="text-slate-300 mb-2">Перетащите файл или кликните для выбора</p>
          <p className="text-slate-500 text-sm">Видео, аудио, изображения</p>
        </>
      )}
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Create assets/page.tsx**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { SourceAsset } from "@/types/api";
import api from "@/lib/api";
import { AssetUpload } from "@/components/assets/AssetUpload";

const STATUS_LABEL: Record<string, string> = {
  uploaded: "Загружен",
  processing: "Обработка...",
  ready: "Готов",
  failed: "Ошибка",
};

const TYPE_ICON: Record<string, string> = {
  video: "🎬",
  audio: "🎙️",
  image: "🖼️",
  text: "📄",
};

export default function AssetsPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [assets, setAssets] = useState<SourceAsset[]>([]);
  const [brand, setBrand] = useState<{ id: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ws) return;
    api.get(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrand(r.data);
      return api.get(`/assets/?brand_id=${r.data.id}`);
    }).then((r) => {
      setAssets(r.data);
    }).finally(() => setLoading(false));
  }, [ws]);

  const handleUploaded = (asset: SourceAsset) => {
    setAssets((prev) => [asset, ...prev]);
  };

  const handleDelete = async (assetId: number) => {
    await api.delete(`/assets/${assetId}`);
    setAssets((prev) => prev.filter((a) => a.id !== assetId));
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;
  if (loading) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-100 mb-6">Asset Library</h1>
      {brand && (
        <div className="mb-6">
          <AssetUpload brandId={brand.id} onUploaded={handleUploaded} />
        </div>
      )}

      {assets.length === 0 ? (
        <p className="text-slate-400 text-center py-12">Нет загруженных файлов</p>
      ) : (
        <div className="grid gap-3">
          {assets.map((asset) => (
            <div
              key={asset.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{TYPE_ICON[asset.asset_type] ?? "📁"}</span>
                <div>
                  <p className="text-slate-100 font-medium">{asset.name}</p>
                  <p className="text-slate-500 text-xs">
                    {STATUS_LABEL[asset.status] ?? asset.status}
                    {asset.file_size && ` · ${(asset.file_size / 1024 / 1024).toFixed(1)} MB`}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(asset.id)}
                className="text-slate-500 hover:text-red-400 transition-colors text-sm"
              >
                Удалить
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add Assets link to Sidebar**

Read `frontend/src/components/layout/Sidebar.tsx` first, then add the link alongside existing navigation items:

```tsx
{ href: "/assets", label: "Asset Library", icon: "📁" },
```

(Add in the same format as existing nav links)

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(dashboard\)/assets/ frontend/src/components/assets/ frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: add Asset Library frontend page with upload"
```

---

## Task 13: Frontend — Drafts & Approval Page

**Files:**
- Create: `frontend/src/app/(dashboard)/drafts/page.tsx`
- Create: `frontend/src/components/drafts/DraftCard.tsx`

- [ ] **Step 1: Create DraftCard.tsx**

```tsx
"use client";
import { Draft } from "@/types/api";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  draft: "bg-slate-700 text-slate-300",
  needs_review: "bg-amber-900 text-amber-300",
  approved: "bg-emerald-900 text-emerald-300",
  rejected: "bg-red-900 text-red-300",
  published: "bg-sky-900 text-sky-300",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Черновик",
  needs_review: "На проверке",
  approved: "Одобрен",
  rejected: "Отклонён",
  published: "Опубликован",
};

interface Props {
  draft: Draft;
  onUpdated: (draft: Draft) => void;
}

export function DraftCard({ draft, onUpdated }: Props) {
  const canSubmit = draft.status === "draft" || draft.status === "rejected";
  const canApprove = draft.status === "needs_review";

  const submit = async () => {
    const res = await api.post(`/drafts/${draft.id}/submit`);
    onUpdated(res.data);
  };

  const approve = async () => {
    const res = await api.post(`/approvals/${draft.id}/approve`, { comment: "" });
    onUpdated(res.data);
  };

  const reject = async () => {
    const comment = prompt("Причина отклонения:");
    if (comment === null) return;
    const res = await api.post(`/approvals/${draft.id}/reject`, { comment });
    onUpdated(res.data);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-sm">{draft.network} · {draft.format} · {draft.funnel_stage}</span>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full ${STATUS_COLOR[draft.status] ?? "bg-slate-700 text-slate-300"}`}>
          {STATUS_LABEL[draft.status] ?? draft.status}
        </span>
      </div>

      {draft.text && (
        <p className="text-slate-200 text-sm whitespace-pre-wrap">{draft.text}</p>
      )}

      {draft.hashtags.length > 0 && (
        <p className="text-sky-400 text-sm">{draft.hashtags.map((h) => `#${h}`).join(" ")}</p>
      )}

      <div className="flex gap-2 pt-1">
        {canSubmit && (
          <Button size="sm" onClick={submit}>На проверку</Button>
        )}
        {canApprove && (
          <>
            <Button size="sm" onClick={approve} className="bg-emerald-600 hover:bg-emerald-700">Одобрить</Button>
            <Button size="sm" onClick={reject} variant="outline" className="border-red-700 text-red-400 hover:bg-red-950">Отклонить</Button>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create drafts/page.tsx**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { Draft } from "@/types/api";
import api from "@/lib/api";
import { DraftCard } from "@/components/drafts/DraftCard";
import { Button } from "@/components/ui/button";

const NETWORKS = ["instagram", "vk", "telegram"];
const FORMATS: Record<string, string[]> = {
  instagram: ["carousel", "reels", "static_post", "story"],
  vk: ["clip", "long_post", "poll", "long_video"],
  telegram: ["longread", "image_post", "poll", "voice", "link"],
};
const STAGES = ["tofu", "mofu", "bofu", "retention"];

export default function DraftsPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [brand, setBrand] = useState<{ id: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [network, setNetwork] = useState("instagram");
  const [format, setFormat] = useState("carousel");
  const [stage, setStage] = useState("tofu");

  useEffect(() => {
    if (!ws) return;
    api.get(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrand(r.data);
      return api.get(`/drafts/?brand_id=${r.data.id}`);
    }).then((r) => {
      setDrafts(r.data);
    }).finally(() => setLoading(false));
  }, [ws]);

  const generate = async () => {
    if (!brand) return;
    setGenerating(true);
    try {
      await api.post("/drafts/generate", {
        brand_id: brand.id,
        network,
        format,
        funnel_stage: stage,
      });
      // Refresh after a short delay (task is async)
      setTimeout(async () => {
        const r = await api.get(`/drafts/?brand_id=${brand.id}`);
        setDrafts(r.data);
        setGenerating(false);
      }, 3000);
    } catch {
      setGenerating(false);
    }
  };

  const handleUpdated = (updated: Draft) => {
    setDrafts((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;
  if (loading) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Черновики</h1>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 mb-6 flex flex-wrap gap-3 items-end">
        <div>
          <label className="text-slate-400 text-xs block mb-1">Сеть</label>
          <select
            value={network}
            onChange={(e) => { setNetwork(e.target.value); setFormat(FORMATS[e.target.value][0]); }}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm"
          >
            {NETWORKS.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div>
          <label className="text-slate-400 text-xs block mb-1">Формат</label>
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm"
          >
            {(FORMATS[network] ?? []).map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div>
          <label className="text-slate-400 text-xs block mb-1">Воронка</label>
          <select
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm"
          >
            {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <Button onClick={generate} disabled={generating}>
          {generating ? "Генерируем..." : "Сгенерировать"}
        </Button>
      </div>

      {drafts.length === 0 ? (
        <p className="text-slate-400 text-center py-12">Нет черновиков</p>
      ) : (
        <div className="space-y-4">
          {drafts.map((draft) => (
            <DraftCard key={draft.id} draft={draft} onUpdated={handleUpdated} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add Drafts link to Sidebar** (same as Task 12 step 3 approach)

Add in nav links:
```tsx
{ href: "/drafts", label: "Черновики", icon: "📝" },
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(dashboard\)/drafts/ frontend/src/components/drafts/ frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: add Drafts & Approval frontend page"
```

---

## Task 14: Frontend — Human Tasks Page

**Files:**
- Create: `frontend/src/app/(dashboard)/tasks/page.tsx`

- [ ] **Step 1: Create tasks/page.tsx**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { HumanTask } from "@/types/api";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-slate-700 text-slate-300",
  in_progress: "bg-amber-900 text-amber-300",
  completed: "bg-emerald-900 text-emerald-300",
  cancelled: "bg-red-900 text-red-300",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Ожидает",
  in_progress: "В работе",
  completed: "Выполнено",
  cancelled: "Отменено",
};

export default function TasksPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [tasks, setTasks] = useState<HumanTask[]>([]);
  const [brand, setBrand] = useState<{ id: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!ws) return;
    api.get(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrand(r.data);
      return api.get(`/human-tasks/?brand_id=${r.data.id}`);
    }).then((r) => {
      setTasks(r.data);
    }).finally(() => setLoading(false));
  }, [ws]);

  const createTask = async () => {
    if (!brand || !newTitle.trim()) return;
    setCreating(true);
    try {
      const res = await api.post("/human-tasks/", {
        brand_id: brand.id,
        title: newTitle,
        description: newDesc || undefined,
      });
      setTasks((prev) => [res.data, ...prev]);
      setNewTitle("");
      setNewDesc("");
    } finally {
      setCreating(false);
    }
  };

  const completeTask = async (taskId: number) => {
    const res = await api.patch(`/human-tasks/${taskId}/complete`, {});
    setTasks((prev) => prev.map((t) => (t.id === taskId ? res.data : t)));
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;
  if (loading) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-100 mb-6">Задачи команде</h1>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6 space-y-3">
        <h2 className="text-slate-300 font-medium">Новая задача</h2>
        <div>
          <Label>Название</Label>
          <Input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Снять вводное видео"
          />
        </div>
        <div>
          <Label>Описание</Label>
          <Input
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Детали задачи..."
          />
        </div>
        <Button onClick={createTask} disabled={creating || !newTitle.trim()}>
          {creating ? "Создаём..." : "Создать задачу"}
        </Button>
      </div>

      {tasks.length === 0 ? (
        <p className="text-slate-400 text-center py-12">Нет задач</p>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between"
            >
              <div>
                <p className="text-slate-100 font-medium">{task.title}</p>
                {task.description && (
                  <p className="text-slate-400 text-sm mt-0.5">{task.description}</p>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${STATUS_COLOR[task.status]}`}>
                  {STATUS_LABEL[task.status] ?? task.status}
                </span>
              </div>
              {task.status === "pending" && (
                <Button size="sm" onClick={() => completeTask(task.id)} variant="outline">
                  Выполнено
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add Tasks link to Sidebar**

Add:
```tsx
{ href: "/tasks", label: "Задачи", icon: "✅" },
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 0 errors

- [ ] **Step 4: Run full backend test suite one last time**

```bash
cd backend
pytest -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(dashboard\)/tasks/ frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: add Human Tasks frontend page"
```

---

## Final Verification

- [ ] All backend tests pass: `cd backend && pytest -v`
- [ ] TypeScript compiles: `cd frontend && npx tsc --noEmit`
- [ ] New routes visible in Swagger: `GET /api/docs` shows `/assets/`, `/drafts/`, `/approvals/`, `/human-tasks/`
- [ ] Sidebar shows: Asset Library, Черновики, Задачи links
- [ ] Asset upload flow works end-to-end (local dev): initiate → confirm → list
- [ ] Draft generation (mocked Celery): POST /drafts/generate returns 202
- [ ] Approval workflow: submit → approve/reject → status changes
- [ ] Human task: create → complete → status = completed

---

## Spec Coverage Check

| Phase 2 Requirement | Covered By |
|---|---|
| Asset Library: upload, storage, tagging, search | Task 4 (storage), Task 5 (API) |
| Repurposing: Whisper transcription | Task 6 |
| Repurposing: PySceneDetect + FFmpeg clips | Task 6 |
| Repurposing: content atom extraction | Task 6 |
| Research path: Tavily web search | Task 8 |
| Draft generator: Claude API per network/format | Task 8 |
| Approval workflow: review queue, approve/reject/comment | Task 9 |
| Draft version history | Task 7 (PATCH creates DraftVersion) |
| Human task: create, complete, handoff | Task 10 |
| Frontend: Asset Library page | Task 12 |
| Frontend: Drafts & Approval page | Task 13 |
| Frontend: Human Tasks page | Task 14 |
| Draft status lifecycle (draft→needs_review→approved/rejected) | Task 7 + Task 9 |
| All heavy jobs in Worker, not blocking API | Task 3 + Tasks 6, 8 (Celery tasks) |
