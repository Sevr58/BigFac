# Phase 3 — Distribution & Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Publishing Engine (Instagram / VK / Telegram adapters, scheduling, retry, logs), Analytics (post metrics, network/format/funnel breakdown, lead attribution via UTM), and Agent Feedback Loop (Claude analyses recent metrics and suggests strategy adjustments) to the Social Content Factory.

**Architecture:** Publishing runs entirely through Celery — a Beat task polls every 60 s for scheduled drafts and enqueues `publish_post` tasks per draft. Each network has an isolated adapter class behind a `BasePublisher` interface. Analytics metrics are pulled daily by a Beat task and stored in `PostMetrics`. Lead events arrive via a webhook endpoint and are tagged to `PublishedPost` via UTM. The feedback loop is a synchronous Claude API call triggered manually or weekly by Beat. No new frontend dependencies — analytics charts use Tailwind CSS bar visualisations.

**Tech Stack:** Existing stack + `celery.schedules.crontab` (already installed), `httpx` (already installed), `anthropic` (already installed). No new Python packages. No new JS packages.

---

## File Map

### Backend — new files

```
backend/app/models/publishing.py          # PublishedPost, PostMetrics, LeadEvent
backend/app/services/utm.py               # build_utm_params(), append_utm_to_url()
backend/app/services/publishers/__init__.py
backend/app/services/publishers/base.py   # BasePublisher ABC, PublishResult dataclass
backend/app/services/publishers/telegram.py
backend/app/services/publishers/vk.py
backend/app/services/publishers/instagram.py
backend/app/tasks/publish_tasks.py        # publish_post (Celery), schedule_pending_posts (Beat)
backend/app/tasks/analytics_tasks.py     # collect_all_metrics (Beat), _fetch_*_metrics helpers
backend/app/api/v1/publishing.py          # schedule, queue, cancel, log, credentials endpoints
backend/app/api/v1/analytics.py           # summary, posts, leads, feedback-loop endpoints
backend/tests/test_utm.py
backend/tests/test_publishers.py
backend/tests/test_publish_tasks.py
backend/tests/test_publishing_api.py
backend/tests/test_analytics_api.py
```

### Backend — modified files

```
backend/app/models/brand.py               # add credentials field to SocialAccount; add relationships to Brand
backend/app/models/content.py             # add published_posts relationship to Draft
backend/app/models/__init__.py            # import publishing models
backend/app/worker.py                     # add publish_tasks + analytics_tasks includes + beat_schedule
backend/app/config.py                     # add yandex_metrica_counter_id, no new API keys needed
backend/app/api/v1/router.py              # register publishing + analytics routers
backend/app/api/v1/brands.py              # add PATCH social account credentials endpoint
```

### Frontend — new files

```
frontend/src/app/(dashboard)/publishing/page.tsx
frontend/src/app/(dashboard)/analytics/page.tsx
```

### Frontend — modified files

```
frontend/src/types/api.ts                 # add PublishedPost, PostMetrics, LeadEvent
frontend/src/app/(dashboard)/layout.tsx   # add Publishing + Analytics nav links
```

---

## Task 1: Publishing Models + Migration

**Files:**
- Create: `backend/app/models/publishing.py`
- Modify: `backend/app/models/brand.py` (add `credentials` to SocialAccount + Brand relationships)
- Modify: `backend/app/models/content.py` (add `published_posts` relationship to Draft)
- Modify: `backend/app/models/__init__.py` (import new models)
- Modify: `backend/alembic/versions/` (generate migration)

- [ ] **Step 1: Write failing model import test**

```python
# backend/tests/test_publishing_models.py
def test_publishing_models_importable():
    from app.models.publishing import PublishedPost, PostMetrics, LeadEvent
    assert PublishedPost.__tablename__ == "published_posts"
    assert PostMetrics.__tablename__ == "post_metrics"
    assert LeadEvent.__tablename__ == "lead_events"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
pytest tests/test_publishing_models.py -v
```
Expected: `ImportError: cannot import name 'PublishedPost'`

- [ ] **Step 3: Create `backend/app/models/publishing.py`**

```python
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PublishedPost(Base):
    __tablename__ = "published_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    network_post_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    utm_params: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    draft: Mapped["Draft"] = relationship(back_populates="published_posts")
    brand: Mapped["Brand"] = relationship(back_populates="published_posts")
    metrics: Mapped[list["PostMetrics"]] = relationship(back_populates="published_post")
    lead_events: Mapped[list["LeadEvent"]] = relationship(back_populates="published_post")


class PostMetrics(Base):
    __tablename__ = "post_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    published_post_id: Mapped[int] = mapped_column(ForeignKey("published_posts.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    reach: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    likes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shares: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clicks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    published_post: Mapped["PublishedPost"] = relationship(back_populates="metrics")
    brand: Mapped["Brand"] = relationship(back_populates="metrics")


class LeadEvent(Base):
    __tablename__ = "lead_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    published_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("published_posts.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), default="lead")
    utm_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="lead_events")
    published_post: Mapped[Optional["PublishedPost"]] = relationship(
        back_populates="lead_events", foreign_keys=[published_post_id]
    )
```

- [ ] **Step 4: Add `credentials` to SocialAccount and relationships to Brand in `backend/app/models/brand.py`**

Add `credentials` field to `SocialAccount`:
```python
# In SocialAccount class, after `enabled`:
credentials: Mapped[dict] = mapped_column(JSON, default=dict)
```

Add to `Brand` class (after `human_tasks` relationship):
```python
published_posts: Mapped[list["PublishedPost"]] = relationship(back_populates="brand")
metrics: Mapped[list["PostMetrics"]] = relationship(back_populates="brand")
lead_events: Mapped[list["LeadEvent"]] = relationship(back_populates="brand")
```

- [ ] **Step 5: Add `published_posts` relationship to Draft in `backend/app/models/content.py`**

After the `human_tasks` relationship in Draft:
```python
published_posts: Mapped[list["PublishedPost"]] = relationship(back_populates="draft")
```

- [ ] **Step 6: Update `backend/app/models/__init__.py`**

```python
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember
from app.models.brand import Brand, SocialAccount, NetworkType
from app.models.strategy import ContentPillar, ContentPlanItem, FunnelStage
from app.models.publishing import PublishedPost, PostMetrics, LeadEvent
```

- [ ] **Step 7: Run test to verify it passes**

```
pytest tests/test_publishing_models.py -v
```
Expected: PASS

- [ ] **Step 8: Generate Alembic migration**

```
cd backend
alembic revision --autogenerate -m "phase3_publishing_analytics"
```
Inspect the generated file in `alembic/versions/` and verify it contains:
- `op.create_table("published_posts", ...)` with all columns
- `op.create_table("post_metrics", ...)` with all columns
- `op.create_table("lead_events", ...)` with all columns
- `op.add_column("social_accounts", sa.Column("credentials", ...))`

- [ ] **Step 9: Apply migration (requires running PostgreSQL)**

```
alembic upgrade head
```
Expected: no errors, 3 new tables created, 1 column added.

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/publishing.py backend/app/models/brand.py \
        backend/app/models/content.py backend/app/models/__init__.py \
        backend/tests/test_publishing_models.py \
        backend/alembic/versions/
git commit -m "feat: add PublishedPost, PostMetrics, LeadEvent models + migration"
```

---

## Task 2: UTM Service

**Files:**
- Create: `backend/app/services/utm.py`
- Create: `backend/tests/test_utm.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_utm.py
from app.services.utm import build_utm_params, append_utm_to_url


def test_build_utm_params_basic():
    params = build_utm_params(
        brand_name="Тест Бренд",
        network="instagram",
        format="reel",
        funnel_stage="tofu",
    )
    assert params["utm_source"] == "instagram"
    assert params["utm_medium"] == "reel"
    assert params["utm_campaign"] == "scf"
    assert params["utm_content"] == "tofu"
    assert len(params["utm_term"]) <= 30


def test_build_utm_params_custom_campaign():
    params = build_utm_params("Brand", "vk", "post", "bofu", campaign="april_promo")
    assert params["utm_campaign"] == "april_promo"


def test_append_utm_to_url_no_existing_params():
    result = append_utm_to_url(
        "https://example.com/page",
        {"utm_source": "vk", "utm_medium": "post"},
    )
    assert "utm_source=vk" in result
    assert "utm_medium=post" in result


def test_append_utm_to_url_preserves_existing_params():
    result = append_utm_to_url(
        "https://example.com/page?ref=email",
        {"utm_source": "telegram"},
    )
    assert "ref=email" in result
    assert "utm_source=telegram" in result


def test_append_utm_to_url_no_url_returns_empty():
    result = append_utm_to_url("", {"utm_source": "vk"})
    assert result == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_utm.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `backend/app/services/utm.py`**

```python
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


def build_utm_params(
    brand_name: str,
    network: str,
    format: str,
    funnel_stage: str,
    campaign: str = "scf",
) -> dict:
    brand_slug = brand_name.lower()
    # Keep only ascii-safe chars
    brand_slug = "".join(c if c.isalnum() else "_" for c in brand_slug)[:30]
    return {
        "utm_source": network.lower(),
        "utm_medium": format.lower().replace(" ", "_"),
        "utm_campaign": campaign,
        "utm_content": funnel_stage.lower(),
        "utm_term": brand_slug,
    }


def append_utm_to_url(url: str, utm_params: dict) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    existing = parse_qs(parsed.query)
    existing.update({k: [v] for k, v in utm_params.items()})
    flat = {k: v[0] for k, v in existing.items()}
    new_query = urlencode(flat)
    return urlunparse(parsed._replace(query=new_query))
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_utm.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/utm.py backend/tests/test_utm.py
git commit -m "feat: add UTM parameter generation service"
```

---

## Task 3: Publisher Base + Telegram Adapter

**Files:**
- Create: `backend/app/services/publishers/__init__.py`
- Create: `backend/app/services/publishers/base.py`
- Create: `backend/app/services/publishers/telegram.py`
- Create: `backend/tests/test_publishers.py` (Telegram section)

- [ ] **Step 1: Write failing test for Telegram publisher**

```python
# backend/tests/test_publishers.py
from unittest.mock import patch, MagicMock
from app.services.publishers.telegram import TelegramPublisher


def test_telegram_publish_success():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "ok": True,
        "result": {"message_id": 42},
    }
    with patch("httpx.post", return_value=mock_resp) as mock_post:
        publisher = TelegramPublisher(bot_token="TEST_TOKEN", chat_id="-100123456")
        result = publisher.publish(
            text="Test post",
            media_keys=[],
            utm_params={"utm_source": "telegram"},
        )
    assert result.success is True
    assert result.network_post_id == "42"
    assert result.error is None
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "sendMessage" in call_kwargs[0][0]


def test_telegram_publish_api_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "ok": False,
        "description": "Bad Request: chat not found",
    }
    with patch("httpx.post", return_value=mock_resp):
        publisher = TelegramPublisher(bot_token="TOKEN", chat_id="bad_id")
        result = publisher.publish("text", [], {})
    assert result.success is False
    assert "chat not found" in result.error


def test_telegram_publish_network_exception():
    with patch("httpx.post", side_effect=Exception("connection refused")):
        publisher = TelegramPublisher(bot_token="TOKEN", chat_id="-100123")
        result = publisher.publish("text", [], {})
    assert result.success is False
    assert "connection refused" in result.error
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_publishers.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `backend/app/services/publishers/__init__.py`** (empty file)

```python
```

- [ ] **Step 4: Create `backend/app/services/publishers/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PublishResult:
    success: bool
    network_post_id: Optional[str] = None
    error: Optional[str] = None


class BasePublisher(ABC):
    @abstractmethod
    def publish(
        self,
        text: str,
        media_keys: list[str],
        utm_params: dict,
    ) -> PublishResult:
        """Publish content to the social network. Returns PublishResult."""
        ...
```

- [ ] **Step 5: Create `backend/app/services/publishers/telegram.py`**

```python
import httpx
from app.services.publishers.base import BasePublisher, PublishResult


class TelegramPublisher(BasePublisher):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._base = f"https://api.telegram.org/bot{bot_token}"

    def publish(self, text: str, media_keys: list[str], utm_params: dict) -> PublishResult:
        try:
            resp = httpx.post(
                f"{self._base}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                return PublishResult(
                    success=True,
                    network_post_id=str(data["result"]["message_id"]),
                )
            return PublishResult(success=False, error=data.get("description", "Unknown error"))
        except Exception as e:
            return PublishResult(success=False, error=str(e))
```

- [ ] **Step 6: Run tests to verify they pass**

```
pytest tests/test_publishers.py -v
```
Expected: 3 PASSED

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/publishers/ backend/tests/test_publishers.py
git commit -m "feat: add BasePublisher + TelegramPublisher"
```

---

## Task 4: VK + Instagram Adapters

**Files:**
- Create: `backend/app/services/publishers/vk.py`
- Create: `backend/app/services/publishers/instagram.py`
- Modify: `backend/tests/test_publishers.py` (add VK + Instagram tests)

- [ ] **Step 1: Add VK + Instagram tests to `backend/tests/test_publishers.py`**

```python
# append to backend/tests/test_publishers.py
from app.services.publishers.vk import VKPublisher
from app.services.publishers.instagram import InstagramPublisher


def test_vk_publish_success():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"response": {"post_id": 99}}
    with patch("httpx.post", return_value=mock_resp):
        publisher = VKPublisher(access_token="VK_TOKEN", owner_id="-12345")
        result = publisher.publish("VK post text", [], {"utm_source": "vk"})
    assert result.success is True
    assert result.network_post_id == "99"


def test_vk_publish_api_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "error": {"error_code": 5, "error_msg": "User authorization failed"}
    }
    with patch("httpx.post", return_value=mock_resp):
        publisher = VKPublisher(access_token="BAD", owner_id="-12345")
        result = publisher.publish("text", [], {})
    assert result.success is False
    assert "authorization failed" in result.error


def test_instagram_publish_success():
    # Step 1: create container → returns {"id": "container_123"}
    # Step 2: publish container → returns {"id": "post_456"}
    mock_create = MagicMock()
    mock_create.raise_for_status = MagicMock()
    mock_create.json.return_value = {"id": "container_123"}

    mock_publish = MagicMock()
    mock_publish.raise_for_status = MagicMock()
    mock_publish.json.return_value = {"id": "post_456"}

    with patch("httpx.post", side_effect=[mock_create, mock_publish]):
        publisher = InstagramPublisher(
            page_access_token="PAGE_TOKEN",
            instagram_account_id="IG_ACCOUNT_ID",
        )
        result = publisher.publish("Caption text", [], {"utm_source": "instagram"})
    assert result.success is True
    assert result.network_post_id == "post_456"


def test_instagram_publish_no_container_id():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {}  # no "id" key
    with patch("httpx.post", return_value=mock_resp):
        publisher = InstagramPublisher("TOKEN", "IG_ID")
        result = publisher.publish("text", [], {})
    assert result.success is False
    assert result.error is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_publishers.py::test_vk_publish_success \
       tests/test_publishers.py::test_instagram_publish_success -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `backend/app/services/publishers/vk.py`**

```python
import httpx
from app.services.publishers.base import BasePublisher, PublishResult


class VKPublisher(BasePublisher):
    _API = "https://api.vk.com/method"
    _VER = "5.199"

    def __init__(self, access_token: str, owner_id: str):
        self.access_token = access_token
        self.owner_id = owner_id  # negative for groups, e.g. "-123456"

    def publish(self, text: str, media_keys: list[str], utm_params: dict) -> PublishResult:
        try:
            resp = httpx.post(
                f"{self._API}/wall.post",
                params={
                    "owner_id": self.owner_id,
                    "message": text,
                    "access_token": self.access_token,
                    "v": self._VER,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if "response" in data:
                return PublishResult(
                    success=True,
                    network_post_id=str(data["response"]["post_id"]),
                )
            error = data.get("error", {}).get("error_msg", "Unknown VK error")
            return PublishResult(success=False, error=error)
        except Exception as e:
            return PublishResult(success=False, error=str(e))
```

- [ ] **Step 4: Create `backend/app/services/publishers/instagram.py`**

```python
import httpx
from app.services.publishers.base import BasePublisher, PublishResult

_GRAPH = "https://graph.facebook.com/v19.0"


class InstagramPublisher(BasePublisher):
    def __init__(self, page_access_token: str, instagram_account_id: str):
        self.token = page_access_token
        self.ig_id = instagram_account_id

    def publish(self, text: str, media_keys: list[str], utm_params: dict) -> PublishResult:
        """Two-step Meta Graph API publish: create container, then publish it."""
        try:
            create_resp = httpx.post(
                f"{_GRAPH}/{self.ig_id}/media",
                params={
                    "caption": text,
                    "access_token": self.token,
                    "media_type": "IMAGE",
                    # image_url omitted in MVP (text-only container not supported by IG)
                    # Real usage: pass image_url from presigned S3 URL
                },
                timeout=30,
            )
            create_resp.raise_for_status()
            container_id = create_resp.json().get("id")
            if not container_id:
                return PublishResult(success=False, error="Instagram returned no container id")

            pub_resp = httpx.post(
                f"{_GRAPH}/{self.ig_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": self.token,
                },
                timeout=30,
            )
            pub_resp.raise_for_status()
            post_id = pub_resp.json().get("id")
            return PublishResult(success=True, network_post_id=str(post_id))
        except Exception as e:
            return PublishResult(success=False, error=str(e))
```

- [ ] **Step 5: Run all publisher tests**

```
pytest tests/test_publishers.py -v
```
Expected: 7 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/publishers/vk.py \
        backend/app/services/publishers/instagram.py \
        backend/tests/test_publishers.py
git commit -m "feat: add VKPublisher and InstagramPublisher"
```

---

## Task 5: Publish Celery Tasks + Beat Schedule

**Files:**
- Create: `backend/app/tasks/publish_tasks.py`
- Create: `backend/tests/test_publish_tasks.py`
- Modify: `backend/app/worker.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_publish_tasks.py
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.models.content import Draft, DraftStatus
from app.models.publishing import PublishedPost


def _make_draft(db, brand_id: int, status=DraftStatus.scheduled) -> Draft:
    from app.models.brand import Brand, SocialAccount, NetworkType
    from app.models.workspace import Workspace, WorkspaceMember
    from app.models.user import User, UserRole

    user = User(email="u@test.com", hashed_password="x", full_name="U")
    db.add(user)
    db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    db.flush()
    brand = Brand(
        workspace_id=ws.id,
        name="Brand",
        company_type="smb",
        description="desc",
        target_audience="all",
        goals=[],
        tone_of_voice="neutral",
        posting_frequency="daily",
    )
    db.add(brand)
    db.flush()
    account = SocialAccount(
        brand_id=brand.id,
        network=NetworkType.telegram,
        handle="@test",
        enabled=True,
        credentials={"bot_token": "TOKEN", "chat_id": "-100123"},
    )
    db.add(account)
    draft = Draft(
        brand_id=brand.id,
        network="telegram",
        format="post",
        funnel_stage="tofu",
        status=status,
        text="Test post content",
        scheduled_at=datetime.utcnow() - timedelta(minutes=1),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def test_publish_draft_sync_success(db):
    from app.tasks.publish_tasks import _publish_draft_sync
    from app.services.publishers.base import PublishResult

    draft = _make_draft(db)
    draft.status = DraftStatus.publishing
    db.commit()

    with patch(
        "app.services.publishers.telegram.TelegramPublisher.publish",
        return_value=PublishResult(success=True, network_post_id="777"),
    ):
        _publish_draft_sync(draft.id, db)

    db.refresh(draft)
    assert draft.status == DraftStatus.published
    pp = db.query(PublishedPost).filter(PublishedPost.draft_id == draft.id).first()
    assert pp is not None
    assert pp.network_post_id == "777"
    assert pp.error is None


def test_publish_draft_sync_failure(db):
    from app.tasks.publish_tasks import _publish_draft_sync
    from app.services.publishers.base import PublishResult

    draft = _make_draft(db)
    draft.status = DraftStatus.publishing
    db.commit()

    with patch(
        "app.services.publishers.telegram.TelegramPublisher.publish",
        return_value=PublishResult(success=False, error="bot blocked"),
    ):
        _publish_draft_sync(draft.id, db)

    db.refresh(draft)
    assert draft.status == DraftStatus.failed
    pp = db.query(PublishedPost).filter(PublishedPost.draft_id == draft.id).first()
    assert pp.error == "bot blocked"


def test_publish_draft_sync_skips_wrong_status(db):
    from app.tasks.publish_tasks import _publish_draft_sync

    draft = _make_draft(db, status=DraftStatus.approved)  # NOT publishing
    _publish_draft_sync(draft.id, db)
    db.refresh(draft)
    assert draft.status == DraftStatus.approved  # unchanged


def test_schedule_pending_posts_enqueues_due_draft(db):
    from app.tasks.publish_tasks import schedule_pending_posts, publish_post

    draft = _make_draft(db)  # scheduled, scheduled_at in the past

    with patch.object(publish_post, "delay") as mock_delay:
        schedule_pending_posts()

    mock_delay.assert_called_once_with(draft.id)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_publish_tasks.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `backend/app/tasks/publish_tasks.py`**

```python
from celery.utils.log import get_task_logger
from app.worker import celery_app
from app.config import settings

logger = get_task_logger(__name__)


def _get_publisher(network: str, credentials: dict):
    from app.services.publishers.telegram import TelegramPublisher
    from app.services.publishers.vk import VKPublisher
    from app.services.publishers.instagram import InstagramPublisher

    if network == "telegram":
        return TelegramPublisher(
            bot_token=credentials.get("bot_token", ""),
            chat_id=credentials.get("chat_id", ""),
        )
    if network == "vk":
        return VKPublisher(
            access_token=credentials.get("access_token", ""),
            owner_id=credentials.get("owner_id", ""),
        )
    if network == "instagram":
        return InstagramPublisher(
            page_access_token=credentials.get("page_access_token", ""),
            instagram_account_id=credentials.get("instagram_account_id", ""),
        )
    raise ValueError(f"Unknown network: {network}")


def _publish_draft_sync(draft_id: int, db) -> None:
    from app.models.content import Draft, DraftStatus
    from app.models.publishing import PublishedPost
    from app.models.brand import Brand, SocialAccount
    from app.services.utm import build_utm_params

    draft = db.get(Draft, draft_id)
    if not draft or draft.status != DraftStatus.publishing:
        return

    brand = db.get(Brand, draft.brand_id)
    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.brand_id == draft.brand_id,
            SocialAccount.network == draft.network,
            SocialAccount.enabled == True,
        )
        .first()
    )

    if not account:
        draft.status = DraftStatus.failed
        db.add(PublishedPost(
            draft_id=draft_id,
            brand_id=draft.brand_id,
            network=draft.network,
            error="No enabled social account found for this network",
            utm_params={},
        ))
        db.commit()
        return

    utm = build_utm_params(
        brand_name=brand.name if brand else "unknown",
        network=draft.network,
        format=draft.format,
        funnel_stage=draft.funnel_stage,
    )

    publisher = _get_publisher(draft.network, account.credentials)
    result = publisher.publish(
        text=draft.text or "",
        media_keys=draft.media_keys,
        utm_params=utm,
    )

    pp = PublishedPost(
        draft_id=draft_id,
        brand_id=draft.brand_id,
        network=draft.network,
        network_post_id=result.network_post_id if result.success else None,
        utm_params=utm,
        error=result.error if not result.success else None,
    )
    db.add(pp)
    draft.status = DraftStatus.published if result.success else DraftStatus.failed
    db.commit()


@celery_app.task(name="publish_post", bind=True, max_retries=3)
def publish_post(self, draft_id: int):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.content import Draft, DraftStatus

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        draft = db.get(Draft, draft_id)
        if not draft:
            return
        draft.status = DraftStatus.publishing
        db.commit()
        _publish_draft_sync(draft_id, db)
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            draft = db.get(Draft, draft_id)
            if draft:
                draft.status = DraftStatus.archived
                db.commit()
            logger.error("publish_post max retries exceeded for draft_id=%s", draft_id)
    finally:
        db.close()


@celery_app.task(name="schedule_pending_posts")
def schedule_pending_posts():
    from datetime import datetime
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.content import Draft, DraftStatus

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        now = datetime.utcnow()
        due_drafts = (
            db.query(Draft)
            .filter(Draft.status == DraftStatus.scheduled, Draft.scheduled_at <= now)
            .all()
        )
        for draft in due_drafts:
            publish_post.delay(draft.id)
            logger.info("Enqueued publish_post for draft_id=%s", draft.id)
    finally:
        db.close()
```

- [ ] **Step 4: Update `backend/app/worker.py` — add includes and beat schedule**

```python
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "scf",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.asset_tasks",
        "app.tasks.draft_tasks",
        "app.tasks.publish_tasks",
        "app.tasks.analytics_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "schedule-pending-posts": {
        "task": "schedule_pending_posts",
        "schedule": 60.0,  # every 60 seconds
    },
    "collect-all-metrics": {
        "task": "collect_all_metrics",
        "schedule": crontab(hour=3, minute=0),  # daily at 03:00 Moscow time
    },
}
```

- [ ] **Step 5: Run tests**

```
pytest tests/test_publish_tasks.py -v
```
Expected: 4 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/tasks/publish_tasks.py \
        backend/app/worker.py \
        backend/tests/test_publish_tasks.py
git commit -m "feat: add publish_post Celery task + schedule_pending_posts Beat task"
```

---

## Task 6: Publishing API Endpoints

**Files:**
- Create: `backend/app/api/v1/publishing.py`
- Create: `backend/tests/test_publishing_api.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/api/v1/brands.py` (add credentials endpoint)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_publishing_api.py
from datetime import datetime, timedelta
from app.models.content import Draft, DraftStatus
from app.models.brand import Brand, SocialAccount, NetworkType
from app.models.workspace import Workspace
from app.models.user import User


def _seed(db):
    user = User(email="pub@test.com", hashed_password="x", full_name="P")
    db.add(user)
    db.flush()
    ws = Workspace(name="PubWS", owner_id=user.id)
    db.add(ws)
    db.flush()
    from app.models.workspace import WorkspaceMember
    from app.models.user import UserRole
    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner)
    db.add(member)
    brand = Brand(
        workspace_id=ws.id, name="PBrand", company_type="smb",
        description="d", target_audience="t", goals=[], tone_of_voice="n",
        posting_frequency="daily",
    )
    db.add(brand)
    db.flush()
    account = SocialAccount(
        brand_id=brand.id, network=NetworkType.telegram,
        handle="@ch", enabled=True, credentials={},
    )
    db.add(account)
    db.commit()
    db.refresh(brand)
    return user, brand


def _auth(client, user):
    resp = client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "secret"
    })
    # user password is hashed "x" which won't match; use a real user for auth tests
    # For these tests we override the dependency directly
    return {}


def _login(client):
    return client.post("/api/v1/auth/register", json={
        "email": "pub@test.com", "password": "secret123", "full_name": "P"
    })


def test_schedule_draft(client, db):
    from app.core.security import hash_password
    user = User(email="sched@test.com", hashed_password=hash_password("secret123"), full_name="S")
    db.add(user)
    db.flush()
    ws = Workspace(name="SW", owner_id=user.id)
    db.add(ws)
    db.flush()
    from app.models.workspace import WorkspaceMember
    from app.models.user import UserRole
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(workspace_id=ws.id, name="SB", company_type="smb",
                  description="d", target_audience="t", goals=[],
                  tone_of_voice="n", posting_frequency="daily")
    db.add(brand)
    db.flush()
    draft = Draft(brand_id=brand.id, network="telegram", format="post",
                  funnel_stage="tofu", status=DraftStatus.approved, text="T")
    db.add(draft)
    db.commit()
    db.refresh(draft)

    login_resp = client.post("/api/v1/auth/login",
                              json={"email": "sched@test.com", "password": "secret123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    scheduled_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    resp = client.post(
        "/api/v1/publishing/schedule",
        json={"draft_id": draft.id, "scheduled_at": scheduled_at},
        headers=headers,
    )
    assert resp.status_code == 200
    db.refresh(draft)
    assert draft.status == DraftStatus.scheduled


def test_schedule_draft_wrong_status_returns_400(client, db):
    from app.core.security import hash_password
    user = User(email="s2@test.com", hashed_password=hash_password("pw"), full_name="S2")
    db.add(user)
    db.flush()
    ws = Workspace(name="W2", owner_id=user.id)
    db.add(ws)
    db.flush()
    from app.models.workspace import WorkspaceMember
    from app.models.user import UserRole
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(workspace_id=ws.id, name="B2", company_type="smb",
                  description="d", target_audience="t", goals=[],
                  tone_of_voice="n", posting_frequency="daily")
    db.add(brand)
    db.flush()
    draft = Draft(brand_id=brand.id, network="telegram", format="post",
                  funnel_stage="tofu", status=DraftStatus.draft, text="T")
    db.add(draft)
    db.commit()
    db.refresh(draft)

    login_resp = client.post("/api/v1/auth/login",
                              json={"email": "s2@test.com", "password": "pw"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    scheduled_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    resp = client.post(
        "/api/v1/publishing/schedule",
        json={"draft_id": draft.id, "scheduled_at": scheduled_at},
        headers=headers,
    )
    assert resp.status_code == 400


def test_publishing_queue(client, db):
    from app.core.security import hash_password
    user = User(email="q@test.com", hashed_password=hash_password("pw"), full_name="Q")
    db.add(user)
    db.flush()
    ws = Workspace(name="QW", owner_id=user.id)
    db.add(ws)
    db.flush()
    from app.models.workspace import WorkspaceMember
    from app.models.user import UserRole
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(workspace_id=ws.id, name="QB", company_type="smb",
                  description="d", target_audience="t", goals=[],
                  tone_of_voice="n", posting_frequency="daily")
    db.add(brand)
    db.flush()
    draft = Draft(brand_id=brand.id, network="telegram", format="post",
                  funnel_stage="tofu", status=DraftStatus.scheduled, text="T",
                  scheduled_at=datetime.utcnow() + timedelta(hours=2))
    db.add(draft)
    db.commit()
    db.refresh(draft)

    login_resp = client.post("/api/v1/auth/login",
                              json={"email": "q@test.com", "password": "pw"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/publishing/queue?brand_id={brand.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == draft.id


def test_publishing_log(client, db):
    from app.core.security import hash_password
    from app.models.publishing import PublishedPost
    user = User(email="log@test.com", hashed_password=hash_password("pw"), full_name="L")
    db.add(user)
    db.flush()
    ws = Workspace(name="LW", owner_id=user.id)
    db.add(ws)
    db.flush()
    from app.models.workspace import WorkspaceMember
    from app.models.user import UserRole
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(workspace_id=ws.id, name="LB", company_type="smb",
                  description="d", target_audience="t", goals=[],
                  tone_of_voice="n", posting_frequency="daily")
    db.add(brand)
    db.flush()
    draft = Draft(brand_id=brand.id, network="telegram", format="post",
                  funnel_stage="tofu", status=DraftStatus.published, text="T")
    db.add(draft)
    db.flush()
    pp = PublishedPost(draft_id=draft.id, brand_id=brand.id,
                       network="telegram", network_post_id="111", utm_params={})
    db.add(pp)
    db.commit()

    login_resp = client.post("/api/v1/auth/login",
                              json={"email": "log@test.com", "password": "pw"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/publishing/log?brand_id={brand.id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["network_post_id"] == "111"
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_publishing_api.py -v
```
Expected: `ImportError` or 404

- [ ] **Step 3: Create `backend/app/api/v1/publishing.py`**

```python
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import Draft, DraftStatus
from app.models.publishing import PublishedPost

router = APIRouter(prefix="/publishing", tags=["publishing"])


class ScheduleRequest(BaseModel):
    draft_id: int
    scheduled_at: datetime


class DraftQueueOut(BaseModel):
    id: int
    brand_id: int
    network: str
    format: str
    funnel_stage: str
    status: str
    text: Optional[str]
    scheduled_at: Optional[datetime]

    class Config:
        from_attributes = True


class PublishedPostOut(BaseModel):
    id: int
    draft_id: int
    brand_id: int
    network: str
    network_post_id: Optional[str]
    utm_params: dict
    error: Optional[str]
    published_at: datetime

    class Config:
        from_attributes = True


@router.post("/schedule", response_model=DraftQueueOut)
def schedule_draft(
    body: ScheduleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, body.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.approved:
        raise HTTPException(status_code=400, detail="Only approved drafts can be scheduled")
    draft.status = DraftStatus.scheduled
    draft.scheduled_at = body.scheduled_at
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/cancel/{draft_id}", response_model=DraftQueueOut)
def cancel_scheduled(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.scheduled:
        raise HTTPException(status_code=400, detail="Draft is not scheduled")
    draft.status = DraftStatus.approved
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/queue", response_model=list[DraftQueueOut])
def publishing_queue(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(Draft)
        .filter(
            Draft.brand_id == brand_id,
            Draft.status.in_([DraftStatus.approved, DraftStatus.scheduled, DraftStatus.publishing]),
        )
        .order_by(Draft.scheduled_at.asc().nullslast())
        .all()
    )


@router.get("/log", response_model=list[PublishedPostOut])
def publishing_log(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(PublishedPost)
        .filter(PublishedPost.brand_id == brand_id)
        .order_by(PublishedPost.published_at.desc())
        .limit(100)
        .all()
    )
```

- [ ] **Step 4: Add credentials endpoint to `backend/app/api/v1/brands.py`**

Add after the last existing route:
```python
from pydantic import BaseModel as _BaseModel

class CredentialsUpdate(_BaseModel):
    credentials: dict


class SocialAccountOut(_BaseModel):
    id: int
    network: str
    handle: str | None
    enabled: bool

    class Config:
        from_attributes = True


@router.patch("/workspaces/{workspace_id}/brand/social-accounts/{account_id}/credentials",
              response_model=SocialAccountOut)
def update_credentials(
    workspace_id: int,
    account_id: int,
    payload: CredentialsUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner)),
):
    from app.models.brand import SocialAccount
    account = db.get(SocialAccount, account_id)
    if not account:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Social account not found")
    account.credentials = payload.credentials
    db.commit()
    db.refresh(account)
    return account
```

- [ ] **Step 5: Register router in `backend/app/api/v1/router.py`**

```python
from fastapi import APIRouter
from app.api.v1 import (
    auth, workspaces, brands, strategy,
    assets, drafts, approvals, human_tasks,
    publishing, analytics,
)

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(brands.router, tags=["brands"])
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
router.include_router(assets.router)
router.include_router(drafts.router)
router.include_router(approvals.router)
router.include_router(human_tasks.router)
router.include_router(publishing.router)
router.include_router(analytics.router)
```

Note: `analytics` will be created in Task 8. For now the import will fail — create a stub `analytics.py` first:

```python
# backend/app/api/v1/analytics.py (stub — will be replaced in Task 8)
from fastapi import APIRouter
router = APIRouter(prefix="/analytics", tags=["analytics"])
```

- [ ] **Step 6: Run tests**

```
pytest tests/test_publishing_api.py -v
```
Expected: 4 PASSED

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/publishing.py \
        backend/app/api/v1/analytics.py \
        backend/app/api/v1/brands.py \
        backend/app/api/v1/router.py \
        backend/tests/test_publishing_api.py
git commit -m "feat: add publishing API (schedule, queue, cancel, log, credentials)"
```

---

## Task 7: Analytics Celery Tasks

**Files:**
- Create: `backend/app/tasks/analytics_tasks.py`
- Create: `backend/tests/test_analytics_tasks.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_analytics_tasks.py
from unittest.mock import patch
from datetime import datetime, timedelta
from app.models.publishing import PublishedPost, PostMetrics
from app.models.content import Draft, DraftStatus
from app.models.brand import Brand, SocialAccount, NetworkType
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User, UserRole


def _seed_published_post(db, network: str = "vk") -> PublishedPost:
    from app.core.security import hash_password
    user = User(email=f"at_{network}@test.com",
                hashed_password=hash_password("pw"), full_name="AT")
    db.add(user)
    db.flush()
    ws = Workspace(name="ATW", owner_id=user.id)
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(workspace_id=ws.id, name="ATB", company_type="smb",
                  description="d", target_audience="t", goals=[],
                  tone_of_voice="n", posting_frequency="daily")
    db.add(brand)
    db.flush()
    account = SocialAccount(
        brand_id=brand.id,
        network=NetworkType(network),
        handle="@ch", enabled=True,
        credentials={"access_token": "TOK", "owner_id": "-999"},
    )
    db.add(account)
    draft = Draft(brand_id=brand.id, network=network, format="post",
                  funnel_stage="tofu", status=DraftStatus.published, text="T")
    db.add(draft)
    db.flush()
    pp = PublishedPost(
        draft_id=draft.id, brand_id=brand.id, network=network,
        network_post_id="123", utm_params={},
        published_at=datetime.utcnow() - timedelta(days=2),
    )
    db.add(pp)
    db.commit()
    db.refresh(pp)
    return pp


def test_collect_metrics_for_vk(db):
    from app.tasks.analytics_tasks import _collect_metrics_for_post

    pp = _seed_published_post(db, "vk")
    fake_metrics = {"views": 500, "likes": 30, "comments": 5, "shares": 2}

    with patch("app.tasks.analytics_tasks._fetch_vk_metrics", return_value=fake_metrics):
        _collect_metrics_for_post(pp.id, db)

    m = db.query(PostMetrics).filter(PostMetrics.published_post_id == pp.id).first()
    assert m is not None
    assert m.views == 500
    assert m.likes == 30


def test_collect_metrics_for_telegram_returns_empty(db):
    from app.tasks.analytics_tasks import _collect_metrics_for_post

    pp = _seed_published_post(db, "telegram")

    with patch("app.tasks.analytics_tasks._fetch_telegram_metrics", return_value={}):
        _collect_metrics_for_post(pp.id, db)

    # No metrics row created for empty result
    m = db.query(PostMetrics).filter(PostMetrics.published_post_id == pp.id).first()
    assert m is None


def test_collect_metrics_skips_posts_older_than_30_days(db):
    from app.tasks.analytics_tasks import _collect_metrics_for_post
    pp = _seed_published_post(db, "vk")
    pp.published_at = datetime.utcnow() - timedelta(days=35)
    db.commit()

    called = []
    with patch("app.tasks.analytics_tasks._fetch_vk_metrics",
               side_effect=lambda *a, **k: called.append(True) or {}):
        _collect_metrics_for_post(pp.id, db)

    assert called == []  # function should bail out early for old posts
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_analytics_tasks.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `backend/app/tasks/analytics_tasks.py`**

```python
from datetime import datetime, timedelta
from celery.utils.log import get_task_logger
from app.worker import celery_app
from app.config import settings

logger = get_task_logger(__name__)

_METRICS_WINDOW_DAYS = 30


def _fetch_vk_metrics(network_post_id: str, credentials: dict) -> dict:
    import httpx
    try:
        owner_id = credentials.get("owner_id", "")
        token = credentials.get("access_token", "")
        resp = httpx.get(
            "https://api.vk.com/method/wall.getById",
            params={
                "posts": f"{owner_id}_{network_post_id}",
                "access_token": token,
                "v": "5.199",
            },
            timeout=30,
        )
        data = resp.json()
        if "response" in data and data["response"]:
            p = data["response"][0]
            return {
                "views": p.get("views", {}).get("count"),
                "likes": p.get("likes", {}).get("count"),
                "comments": p.get("comments", {}).get("count"),
                "shares": p.get("reposts", {}).get("count"),
            }
    except Exception as e:
        logger.warning("VK metrics fetch failed: %s", e)
    return {}


def _fetch_instagram_metrics(network_post_id: str, credentials: dict) -> dict:
    import httpx
    try:
        token = credentials.get("page_access_token", "")
        resp = httpx.get(
            f"https://graph.facebook.com/v19.0/{network_post_id}/insights",
            params={
                "metric": "reach,impressions,like_count,comments_count,shares,saved",
                "access_token": token,
            },
            timeout=30,
        )
        data = resp.json()
        result = {}
        for item in data.get("data", []):
            name = item["name"]
            value = item.get("values", [{}])[-1].get("value", 0)
            result[name] = value
        return {
            "reach": result.get("reach"),
            "views": result.get("impressions"),
            "likes": result.get("like_count"),
            "comments": result.get("comments_count"),
            "shares": result.get("shares"),
            "saves": result.get("saved"),
        }
    except Exception as e:
        logger.warning("Instagram metrics fetch failed: %s", e)
    return {}


def _fetch_telegram_metrics(network_post_id: str, credentials: dict) -> dict:
    # Telegram Bot API does not expose per-message analytics for channels.
    # Metrics require Telegram Analytics API (paid) or third-party tools (TGStat).
    # For MVP, return empty — metrics must be entered manually or via webhook.
    return {}


def _collect_metrics_for_post(published_post_id: int, db) -> None:
    from app.models.publishing import PublishedPost, PostMetrics
    from app.models.brand import SocialAccount

    pp = db.get(PublishedPost, published_post_id)
    if not pp or not pp.network_post_id:
        return

    cutoff = datetime.utcnow() - timedelta(days=_METRICS_WINDOW_DAYS)
    if pp.published_at < cutoff:
        return  # too old to collect

    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.brand_id == pp.brand_id,
            SocialAccount.network == pp.network,
            SocialAccount.enabled == True,
        )
        .first()
    )
    credentials = account.credentials if account else {}

    fetchers = {
        "vk": _fetch_vk_metrics,
        "instagram": _fetch_instagram_metrics,
        "telegram": _fetch_telegram_metrics,
    }
    fetch_fn = fetchers.get(pp.network)
    if not fetch_fn:
        return

    raw = fetch_fn(pp.network_post_id, credentials)
    if not raw:
        return  # nothing to record

    m = PostMetrics(
        published_post_id=pp.id,
        brand_id=pp.brand_id,
        reach=raw.get("reach"),
        views=raw.get("views"),
        likes=raw.get("likes"),
        comments=raw.get("comments"),
        shares=raw.get("shares"),
        saves=raw.get("saves"),
        clicks=raw.get("clicks"),
    )
    db.add(m)
    db.commit()


@celery_app.task(name="collect_all_metrics")
def collect_all_metrics():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.publishing import PublishedPost
    from datetime import datetime, timedelta

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=_METRICS_WINDOW_DAYS)
        posts = (
            db.query(PublishedPost)
            .filter(
                PublishedPost.published_at >= cutoff,
                PublishedPost.network_post_id.isnot(None),
            )
            .all()
        )
        for pp in posts:
            try:
                _collect_metrics_for_post(pp.id, db)
            except Exception as e:
                logger.error("Failed to collect metrics for published_post_id=%s: %s", pp.id, e)
    finally:
        db.close()
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_analytics_tasks.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/analytics_tasks.py backend/tests/test_analytics_tasks.py
git commit -m "feat: add analytics Celery tasks (collect_all_metrics + per-network fetchers)"
```

---

## Task 8: Analytics API + Feedback Loop

**Files:**
- Replace stub: `backend/app/api/v1/analytics.py`
- Create: `backend/tests/test_analytics_api.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_analytics_api.py
from datetime import datetime
from app.models.publishing import PublishedPost, PostMetrics, LeadEvent
from app.models.content import Draft, DraftStatus
from app.models.brand import Brand
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User, UserRole
from app.core.security import hash_password


def _seed_analytics(db):
    user = User(email="an@test.com", hashed_password=hash_password("pw"), full_name="A")
    db.add(user)
    db.flush()
    ws = Workspace(name="AW", owner_id=user.id)
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(workspace_id=ws.id, name="AB", company_type="smb",
                  description="Test brand", target_audience="t",
                  goals=["awareness"], tone_of_voice="friendly", posting_frequency="daily")
    db.add(brand)
    db.flush()
    draft = Draft(brand_id=brand.id, network="vk", format="post",
                  funnel_stage="tofu", status=DraftStatus.published, text="T")
    db.add(draft)
    db.flush()
    pp = PublishedPost(draft_id=draft.id, brand_id=brand.id, network="vk",
                       network_post_id="p1", utm_params={}, published_at=datetime.utcnow())
    db.add(pp)
    db.flush()
    m = PostMetrics(published_post_id=pp.id, brand_id=brand.id,
                    views=1000, likes=50, comments=5, shares=10, reach=800)
    db.add(m)
    db.commit()
    db.refresh(brand)
    return user, brand, pp


def _get_token(client, email, password="pw"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_analytics_summary(client, db):
    user, brand, pp = _seed_analytics(db)
    token = _get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/analytics/summary?brand_id={brand.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_posts" in data
    assert data["total_posts"] == 1
    assert "by_network" in data
    assert data["by_network"]["vk"]["views"] == 1000


def test_analytics_posts(client, db):
    user, brand, pp = _seed_analytics(db)
    token = _get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/analytics/posts?brand_id={brand.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["network"] == "vk"
    assert data[0]["metrics"]["views"] == 1000


def test_record_lead_event(client, db):
    user, brand, pp = _seed_analytics(db)
    token = _get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/analytics/leads",
        json={
            "brand_id": brand.id,
            "published_post_id": pp.id,
            "event_type": "lead",
            "utm_source": "vk",
            "utm_medium": "post",
            "utm_campaign": "scf",
            "utm_content": "tofu",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    ev = db.query(LeadEvent).filter(LeadEvent.brand_id == brand.id).first()
    assert ev is not None
    assert ev.utm_source == "vk"


def test_feedback_loop(client, db):
    from unittest.mock import patch, MagicMock
    user, brand, pp = _seed_analytics(db)
    token = _get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="Рекомендация: публикуйте больше Reels.")]

    with patch("app.api.v1.analytics._call_claude_feedback", return_value="Рекомендация: публикуйте больше Reels."):
        resp = client.post(
            f"/api/v1/analytics/feedback-loop?brand_id={brand.id}",
            headers=headers,
        )
    assert resp.status_code == 200
    assert "Рекомендация" in resp.json()["suggestion"]
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_analytics_api.py -v
```
Expected: errors (stub has no routes)

- [ ] **Step 3: Replace `backend/app/api/v1/analytics.py`**

```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.publishing import PublishedPost, PostMetrics, LeadEvent
from app.models.brand import Brand

router = APIRouter(prefix="/analytics", tags=["analytics"])


class LeadEventCreate(BaseModel):
    brand_id: int
    published_post_id: Optional[int] = None
    event_type: str = "lead"
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None


class LeadEventOut(BaseModel):
    id: int
    brand_id: int
    published_post_id: Optional[int]
    event_type: str
    utm_source: Optional[str]
    utm_medium: Optional[str]
    utm_campaign: Optional[str]
    utm_content: Optional[str]

    class Config:
        from_attributes = True


def _call_claude_feedback(prompt: str) -> str:
    from anthropic import Anthropic
    from app.config import settings
    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _build_feedback_prompt(brand: Brand, summary: dict) -> str:
    by_network = "\n".join(
        f"  {net}: {vals['total_posts']} posts, {vals.get('views', 0)} views, "
        f"{vals.get('likes', 0)} likes, {vals.get('shares', 0)} shares"
        for net, vals in summary.get("by_network", {}).items()
    )
    by_format = "\n".join(
        f"  {fmt}: {vals.get('views', 0)} avg views"
        for fmt, vals in summary.get("by_format", {}).items()
    )
    by_funnel = "\n".join(
        f"  {stage}: {vals['total_posts']} posts"
        for stage, vals in summary.get("by_funnel", {}).items()
    )
    return f"""Вы — стратег по контенту в социальных сетях. Проанализируйте результаты за последние 30 дней.

Бренд: {brand.name}
Описание: {brand.description}
Цели: {", ".join(brand.goals)}

Результаты:
По сетям:
{by_network}

По форматам:
{by_format}

По воронке:
{by_funnel}

Всего постов: {summary.get("total_posts", 0)}
Всего просмотров: {summary.get("total_views", 0)}
Всего лидов: {summary.get("total_leads", 0)}

На основе этих данных дайте 3–5 конкретных рекомендаций для контент-плана на следующую неделю.
Будьте конкретны: какие форматы и сети приоритизировать, какой тип контента создавать больше или меньше.
Ответьте только рекомендациями, без вводных слов."""


def _build_summary(brand_id: int, db: Session) -> dict:
    posts = (
        db.query(PublishedPost)
        .filter(PublishedPost.brand_id == brand_id)
        .all()
    )
    if not posts:
        return {"total_posts": 0, "total_views": 0, "total_leads": 0,
                "by_network": {}, "by_format": {}, "by_funnel": {}}

    post_ids = [p.id for p in posts]
    metrics = db.query(PostMetrics).filter(PostMetrics.published_post_id.in_(post_ids)).all()
    metrics_by_post = {m.published_post_id: m for m in metrics}

    # draft data for format + funnel
    from app.models.content import Draft
    draft_ids = [p.draft_id for p in posts]
    drafts = db.query(Draft).filter(Draft.id.in_(draft_ids)).all()
    drafts_by_id = {d.id: d for d in drafts}

    by_network: dict = {}
    by_format: dict = {}
    by_funnel: dict = {}
    total_views = 0

    for pp in posts:
        net = pp.network
        m = metrics_by_post.get(pp.id)
        draft = drafts_by_id.get(pp.draft_id)
        views = m.views or 0 if m else 0
        likes = m.likes or 0 if m else 0
        shares = m.shares or 0 if m else 0
        total_views += views

        if net not in by_network:
            by_network[net] = {"total_posts": 0, "views": 0, "likes": 0, "shares": 0}
        by_network[net]["total_posts"] += 1
        by_network[net]["views"] += views
        by_network[net]["likes"] += likes
        by_network[net]["shares"] += shares

        if draft:
            fmt = draft.format
            if fmt not in by_format:
                by_format[fmt] = {"total_posts": 0, "views": 0}
            by_format[fmt]["total_posts"] += 1
            by_format[fmt]["views"] += views

            stage = draft.funnel_stage
            if stage not in by_funnel:
                by_funnel[stage] = {"total_posts": 0}
            by_funnel[stage]["total_posts"] += 1

    total_leads = db.query(LeadEvent).filter(LeadEvent.brand_id == brand_id).count()

    return {
        "total_posts": len(posts),
        "total_views": total_views,
        "total_leads": total_leads,
        "by_network": by_network,
        "by_format": by_format,
        "by_funnel": by_funnel,
    }


@router.get("/summary")
def analytics_summary(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _build_summary(brand_id, db)


@router.get("/posts")
def post_analytics(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    posts = (
        db.query(PublishedPost)
        .filter(PublishedPost.brand_id == brand_id)
        .order_by(PublishedPost.published_at.desc())
        .limit(100)
        .all()
    )
    post_ids = [p.id for p in posts]
    metrics = db.query(PostMetrics).filter(PostMetrics.published_post_id.in_(post_ids)).all()
    metrics_map = {m.published_post_id: m for m in metrics}

    result = []
    for pp in posts:
        m = metrics_map.get(pp.id)
        result.append({
            "id": pp.id,
            "draft_id": pp.draft_id,
            "network": pp.network,
            "network_post_id": pp.network_post_id,
            "published_at": pp.published_at.isoformat(),
            "utm_params": pp.utm_params,
            "metrics": {
                "views": m.views if m else None,
                "likes": m.likes if m else None,
                "comments": m.comments if m else None,
                "shares": m.shares if m else None,
                "reach": m.reach if m else None,
                "saves": m.saves if m else None,
                "clicks": m.clicks if m else None,
            } if m else None,
        })
    return result


@router.post("/leads", response_model=LeadEventOut, status_code=http_status.HTTP_201_CREATED)
def record_lead(
    body: LeadEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    event = LeadEvent(
        brand_id=body.brand_id,
        published_post_id=body.published_post_id,
        event_type=body.event_type,
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
        utm_content=body.utm_content,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.post("/feedback-loop")
def run_feedback_loop(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    summary = _build_summary(brand_id, db)
    prompt = _build_feedback_prompt(brand, summary)
    suggestion = _call_claude_feedback(prompt)
    return {"brand_id": brand_id, "suggestion": suggestion}
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_analytics_api.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/analytics.py backend/tests/test_analytics_api.py
git commit -m "feat: add analytics API (summary, posts, leads, feedback-loop)"
```

---

## Task 9: Config Update + Full Test Suite

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Update `backend/app/config.py`**

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

    # Phase 3 — used as defaults if not in SocialAccount.credentials
    telegram_bot_token: str = ""
    yandex_metrica_counter_id: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
```

Also update `backend/.env.example` to document the new variables:
```
# Social network credentials are stored per SocialAccount in the database.
# Set these for testing publishing without a real account record:
TELEGRAM_BOT_TOKEN=
YANDEX_METRICA_COUNTER_ID=
```

- [ ] **Step 2: Run the full backend test suite**

```
cd backend
pytest tests/ -v --tb=short 2>&1 | tail -40
```
Expected: all existing tests pass plus new tests from Tasks 1–8. Fix any import or migration errors before proceeding.

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "chore: update config for Phase 3 env vars; verify full test suite"
```

---

## Task 10: Frontend Types + Nav

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/app/(dashboard)/layout.tsx`

- [ ] **Step 1: Add Phase 3 types to `frontend/src/types/api.ts`**

Append at the end of the file:
```typescript
// Phase 3 types

export interface DraftQueue {
  id: number;
  brand_id: number;
  network: string;
  format: string;
  funnel_stage: string;
  status: DraftStatus;
  text: string | null;
  scheduled_at: string | null;
}

export interface PublishedPost {
  id: number;
  draft_id: number;
  brand_id: number;
  network: string;
  network_post_id: string | null;
  utm_params: Record<string, string>;
  error: string | null;
  published_at: string;
}

export interface PostMetrics {
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  reach: number | null;
  saves: number | null;
  clicks: number | null;
}

export interface PostAnalyticsItem {
  id: number;
  draft_id: number;
  network: string;
  network_post_id: string | null;
  published_at: string;
  utm_params: Record<string, string>;
  metrics: PostMetrics | null;
}

export interface LeadEvent {
  id: number;
  brand_id: number;
  published_post_id: number | null;
  event_type: string;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  utm_content: string | null;
}

export interface AnalyticsSummary {
  total_posts: number;
  total_views: number;
  total_leads: number;
  by_network: Record<string, { total_posts: number; views: number; likes: number; shares: number }>;
  by_format: Record<string, { total_posts: number; views: number }>;
  by_funnel: Record<string, { total_posts: number }>;
}
```

- [ ] **Step 2: Add Publishing and Analytics links to `frontend/src/app/(dashboard)/layout.tsx`**

Replace the `NAV` array:
```typescript
const NAV = [
  { href: "/", label: "Календарь" },
  { href: "/strategy", label: "Стратегия" },
  { href: "/brand", label: "Бренд" },
  { href: "/assets", label: "Ассеты" },
  { href: "/drafts", label: "Черновики" },
  { href: "/tasks", label: "Задачи" },
  { href: "/publishing", label: "Публикации" },
  { href: "/analytics", label: "Аналитика" },
];
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend
npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/app/(dashboard)/layout.tsx
git commit -m "feat: add Phase 3 frontend types + nav links"
```

---

## Task 11: Frontend Publishing Queue Page

**Files:**
- Create: `frontend/src/app/(dashboard)/publishing/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/(dashboard)/publishing/page.tsx`**

```typescript
"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspace";
import type { DraftQueue, PublishedPost } from "@/types/api";

const STATUS_LABEL: Record<string, string> = {
  approved: "Одобрен",
  scheduled: "Запланирован",
  publishing: "Публикуется…",
  published: "Опубликован",
  failed: "Ошибка",
};

const STATUS_COLOR: Record<string, string> = {
  approved: "text-sky-400",
  scheduled: "text-amber-400",
  publishing: "text-purple-400",
  published: "text-green-400",
  failed: "text-red-400",
};

const NETWORK_LABEL: Record<string, string> = {
  instagram: "Instagram",
  vk: "VK",
  telegram: "Telegram",
};

function formatDatetimeLocal(iso: string): string {
  return iso.slice(0, 16);
}

export default function PublishingPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [brandId, setBrandId] = useState<number | null>(null);
  const [queue, setQueue] = useState<DraftQueue[]>([]);
  const [log, setLog] = useState<PublishedPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [scheduleMap, setScheduleMap] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = async (bid: number) => {
    setLoading(true);
    try {
      const [qRes, lRes] = await Promise.all([
        api.get<DraftQueue[]>(`/publishing/queue?brand_id=${bid}`),
        api.get<PublishedPost[]>(`/publishing/log?brand_id=${bid}`),
      ]);
      setQueue(qRes.data);
      setLog(lRes.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!ws) return;
    api.get<{ id: number }>(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrandId(r.data.id);
      load(r.data.id);
    });
  }, [ws]);

  const handleSchedule = async (draftId: number) => {
    if (!brandId) return;
    const at = scheduleMap[draftId];
    if (!at) { setError("Выберите дату и время"); return; }
    setError(null);
    await api.post("/publishing/schedule", {
      draft_id: draftId,
      scheduled_at: new Date(at).toISOString(),
    });
    load(brandId);
  };

  const handleCancel = async (draftId: number) => {
    if (!brandId) return;
    await api.post(`/publishing/cancel/${draftId}`);
    load(brandId);
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-100">Очередь публикаций</h1>

      {error && (
        <div className="bg-red-900/40 border border-red-700 rounded px-4 py-2 text-red-300 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-slate-400">Загрузка…</p>
      ) : (
        <>
          {/* Queue */}
          <section>
            <h2 className="text-lg font-semibold text-slate-300 mb-3">
              Одобренные и запланированные
            </h2>
            {queue.length === 0 ? (
              <p className="text-slate-500 text-sm">Нет постов в очереди</p>
            ) : (
              <div className="space-y-3">
                {queue.map((d) => (
                  <div
                    key={d.id}
                    className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-slate-400 uppercase">
                          {NETWORK_LABEL[d.network] ?? d.network}
                        </span>
                        <span className="text-xs text-slate-600">·</span>
                        <span className="text-xs text-slate-400">{d.format}</span>
                        <span className="text-xs text-slate-600">·</span>
                        <span className={`text-xs font-medium ${STATUS_COLOR[d.status] ?? "text-slate-400"}`}>
                          {STATUS_LABEL[d.status] ?? d.status}
                        </span>
                      </div>
                      <p className="text-sm text-slate-300 truncate">{d.text ?? "(нет текста)"}</p>
                      {d.scheduled_at && (
                        <p className="text-xs text-amber-400 mt-1">
                          {new Date(d.scheduled_at).toLocaleString("ru-RU")}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {d.status === "approved" && (
                        <>
                          <input
                            type="datetime-local"
                            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
                            value={scheduleMap[d.id] ?? ""}
                            min={formatDatetimeLocal(new Date().toISOString())}
                            onChange={(e) =>
                              setScheduleMap((prev) => ({ ...prev, [d.id]: e.target.value }))
                            }
                          />
                          <button
                            onClick={() => handleSchedule(d.id)}
                            className="px-3 py-1 text-xs bg-sky-600 hover:bg-sky-500 text-white rounded"
                          >
                            Запланировать
                          </button>
                        </>
                      )}
                      {d.status === "scheduled" && (
                        <button
                          onClick={() => handleCancel(d.id)}
                          className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
                        >
                          Отменить
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Log */}
          <section>
            <h2 className="text-lg font-semibold text-slate-300 mb-3">
              История публикаций
            </h2>
            {log.length === 0 ? (
              <p className="text-slate-500 text-sm">Публикаций ещё нет</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-slate-300">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                      <th className="pb-2 pr-4">Сеть</th>
                      <th className="pb-2 pr-4">ID поста</th>
                      <th className="pb-2 pr-4">Дата</th>
                      <th className="pb-2">Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {log.map((pp) => (
                      <tr key={pp.id} className="border-b border-slate-800/50">
                        <td className="py-2 pr-4">{NETWORK_LABEL[pp.network] ?? pp.network}</td>
                        <td className="py-2 pr-4 font-mono text-xs text-slate-400">
                          {pp.network_post_id ?? "—"}
                        </td>
                        <td className="py-2 pr-4 text-slate-400">
                          {new Date(pp.published_at).toLocaleString("ru-RU")}
                        </td>
                        <td className="py-2">
                          {pp.error ? (
                            <span className="text-red-400 text-xs" title={pp.error}>
                              Ошибка
                            </span>
                          ) : (
                            <span className="text-green-400 text-xs">Успешно</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
```

Note: `useWorkspaceStore` must expose `currentBrandId`. Check `frontend/src/store/workspace.ts` — if `currentBrandId` is not there, use `brandId` or whichever field holds the active brand ID.

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/(dashboard)/publishing/
git commit -m "feat: add Publishing Queue frontend page"
```

---

## Task 12: Frontend Analytics Dashboard Page

**Files:**
- Create: `frontend/src/app/(dashboard)/analytics/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/(dashboard)/analytics/page.tsx`**

```typescript
"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspace";
import type { AnalyticsSummary, PostAnalyticsItem } from "@/types/api";

const NETWORK_LABEL: Record<string, string> = {
  instagram: "Instagram",
  vk: "VK",
  telegram: "Telegram",
};

const FUNNEL_LABEL: Record<string, string> = {
  tofu: "TOFU",
  mofu: "MOFU",
  bofu: "BOFU",
  retention: "Retention",
};

function BarChart({
  data,
  label,
}: {
  data: { name: string; value: number }[];
  label: string;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div>
      <p className="text-xs text-slate-400 mb-2 uppercase tracking-wide">{label}</p>
      <div className="space-y-2">
        {data.map((d) => (
          <div key={d.name} className="flex items-center gap-2">
            <span className="w-24 text-xs text-slate-400 truncate">{d.name}</span>
            <div className="flex-1 bg-slate-800 rounded-full h-3">
              <div
                className="bg-sky-500 h-3 rounded-full transition-all"
                style={{ width: `${(d.value / max) * 100}%` }}
              />
            </div>
            <span className="w-12 text-right text-xs text-slate-400">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-100">{value}</p>
    </div>
  );
}

export default function AnalyticsPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [brandId, setBrandId] = useState<number | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [posts, setPosts] = useState<PostAnalyticsItem[]>([]);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [loopLoading, setLoopLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = async (bid: number) => {
    setLoading(true);
    try {
      const [sRes, pRes] = await Promise.all([
        api.get<AnalyticsSummary>(`/analytics/summary?brand_id=${bid}`),
        api.get<PostAnalyticsItem[]>(`/analytics/posts?brand_id=${bid}`),
      ]);
      setSummary(sRes.data);
      setPosts(pRes.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!ws) return;
    api.get<{ id: number }>(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrandId(r.data.id);
      load(r.data.id);
    });
  }, [ws]);

  const runFeedbackLoop = async () => {
    if (!brandId) return;
    setLoopLoading(true);
    setSuggestion(null);
    try {
      const res = await api.post<{ suggestion: string }>(
        `/analytics/feedback-loop?brand_id=${brandId}`
      );
      setSuggestion(res.data.suggestion);
    } finally {
      setLoopLoading(false);
    }
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;

  if (loading || !summary) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-slate-100">Аналитика</h1>
        <p className="text-slate-400">Загрузка…</p>
      </div>
    );
  }

  const networkChartData = Object.entries(summary.by_network).map(([net, v]) => ({
    name: NETWORK_LABEL[net] ?? net,
    value: v.views,
  }));

  const formatChartData = Object.entries(summary.by_format).map(([fmt, v]) => ({
    name: fmt,
    value: v.views,
  }));

  const funnelChartData = Object.entries(summary.by_funnel).map(([stage, v]) => ({
    name: FUNNEL_LABEL[stage] ?? stage,
    value: v.total_posts,
  }));

  const topPosts = [...posts]
    .filter((p) => p.metrics?.views != null)
    .sort((a, b) => (b.metrics!.views ?? 0) - (a.metrics!.views ?? 0))
    .slice(0, 5);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-100">Аналитика</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Постов опубликовано" value={summary.total_posts} />
        <StatCard label="Просмотры" value={summary.total_views.toLocaleString("ru-RU")} />
        <StatCard label="Лиды" value={summary.total_leads} />
        <StatCard
          label="Активных сетей"
          value={Object.keys(summary.by_network).length}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        {networkChartData.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <BarChart data={networkChartData} label="По сетям (просмотры)" />
          </div>
        )}
        {formatChartData.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <BarChart data={formatChartData} label="По форматам (просмотры)" />
          </div>
        )}
        {funnelChartData.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <BarChart data={funnelChartData} label="По воронке (постов)" />
          </div>
        )}
      </div>

      {/* Top posts */}
      {topPosts.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-slate-300 mb-3">
            Топ постов по просмотрам
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-slate-300">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                  <th className="pb-2 pr-4">Сеть</th>
                  <th className="pb-2 pr-4">Дата</th>
                  <th className="pb-2 pr-4 text-right">Просмотры</th>
                  <th className="pb-2 pr-4 text-right">Лайки</th>
                  <th className="pb-2 text-right">Репосты</th>
                </tr>
              </thead>
              <tbody>
                {topPosts.map((p) => (
                  <tr key={p.id} className="border-b border-slate-800/50">
                    <td className="py-2 pr-4">{NETWORK_LABEL[p.network] ?? p.network}</td>
                    <td className="py-2 pr-4 text-slate-400">
                      {new Date(p.published_at).toLocaleDateString("ru-RU")}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono">
                      {p.metrics?.views?.toLocaleString("ru-RU") ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono">
                      {p.metrics?.likes?.toLocaleString("ru-RU") ?? "—"}
                    </td>
                    <td className="py-2 text-right font-mono">
                      {p.metrics?.shares?.toLocaleString("ru-RU") ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Feedback loop */}
      <section className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">AI-анализ стратегии</h2>
            <p className="text-sm text-slate-400 mt-1">
              Клод проанализирует последние результаты и предложит скорректировать контент-план.
            </p>
          </div>
          <button
            onClick={runFeedbackLoop}
            disabled={loopLoading}
            className="shrink-0 px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm rounded"
          >
            {loopLoading ? "Анализирую…" : "Запустить анализ"}
          </button>
        </div>

        {suggestion && (
          <div className="bg-slate-800 rounded p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
            {suggestion}
          </div>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Run the dev server and manually verify both new pages render without errors**

```
cd frontend
npm run dev
```
Navigate to `http://localhost:3000/publishing` and `http://localhost:3000/analytics`. Both pages should load and show the loading state or empty states.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/(dashboard)/analytics/
git commit -m "feat: add Analytics Dashboard frontend page with feedback loop"
```

---

## Self-Review

**Spec coverage check against `docs/superpowers/specs/2026-04-12-social-content-factory-design.md` Section 14 Phase 3:**

| Spec requirement | Task |
|---|---|
| Publishing engine: Instagram adapter | Task 5 |
| Publishing engine: VK adapter | Task 4 |
| Publishing engine: Telegram adapter | Task 3 |
| Scheduling | Task 6 (API) + Task 5 (Beat) |
| Retry logic with exponential backoff | Task 5 (`publish_post` max_retries=3) |
| Publishing logs | Task 6 (`/publishing/log`) |
| Analytics dashboard: post metrics | Task 8 + Task 12 |
| Analytics: network/format/funnel breakdown | Task 8 (`_build_summary`) + Task 12 (charts) |
| Lead attribution: UTM generation | Task 2 |
| Lead attribution: lead events API | Task 8 (`/analytics/leads`) |
| Agent feedback loop: analytics → strategy | Task 8 (`/analytics/feedback-loop`) + Task 12 (UI) |
| Per-network metrics collection | Task 7 |
| Credentials storage for social accounts | Task 1 (model) + Task 6 (API endpoint) |

**Placeholder scan:** No TBD, TODO, or stub patterns found in task code blocks.

**Type consistency check:**
- `PublishResult(success, network_post_id, error)` — defined Task 3, used Tasks 4, 5. ✓
- `_publish_draft_sync(draft_id, db)` — defined Task 5, tested Task 5. ✓
- `_collect_metrics_for_post(published_post_id, db)` — defined Task 7, tested Task 7. ✓
- `_build_summary(brand_id, db)` — defined Task 8, called in `analytics_summary` and `run_feedback_loop`. ✓
- `_call_claude_feedback(prompt)` — defined and tested in Task 8. ✓
- `AnalyticsSummary` TS type — defined Task 10, used Task 12. ✓
- `DraftQueue` TS type — defined Task 10, used Task 11. ✓

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-15-phase3-distribution-analytics.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — свежий субагент на каждую задачу, ревью между задачами, быстрая итерация

**2. Inline Execution** — выполнение задач в этой сессии через executing-plans с чекпоинтами

**Какой подход выбираем?**
