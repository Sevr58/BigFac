# Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the authentication, workspace, role system, brand profile, and strategy engine — the complete foundation that all future phases depend on.

**Architecture:** FastAPI backend with SQLAlchemy ORM and Alembic migrations. Next.js 15 (App Router) frontend with TypeScript and Tailwind CSS. All auth via JWT. Strategy engine calls Claude API to generate content pillars and a 4-week content plan from brand profile data.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, python-jose (JWT), passlib (bcrypt), httpx, anthropic SDK, Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Zustand (client state), React Hook Form + Zod (forms).

---

## File Map

### Backend

```
backend/
  app/
    main.py                        # FastAPI app factory, CORS, routers
    config.py                      # Settings via pydantic-settings (.env)
    database.py                    # SQLAlchemy engine, session, Base
    models/
      __init__.py
      user.py                      # User, UserRole enum
      workspace.py                 # Workspace, WorkspaceMember
      brand.py                     # Brand, SocialNetwork, NetworkType enum
      strategy.py                  # ContentPillar, ContentPlanItem, FunnelStage enum
    schemas/
      __init__.py
      auth.py                      # RegisterRequest, LoginRequest, TokenResponse
      workspace.py                 # WorkspaceCreate, WorkspaceOut, MemberOut
      brand.py                     # BrandCreate, BrandUpdate, BrandOut, NetworkCreate
      strategy.py                  # PillarOut, ContentPlanItemOut, StrategyOut
    api/
      v1/
        __init__.py
        router.py                  # Mounts all sub-routers
        auth.py                    # POST /register, POST /login, GET /me
        workspaces.py              # CRUD workspaces, manage members
        brands.py                  # CRUD brand profile, manage social accounts
        strategy.py                # POST /generate, GET /pillars, GET /plan
    services/
      auth_service.py              # create_user, authenticate, issue_token
      workspace_service.py         # create_workspace, add_member, check_role
      brand_service.py             # create_brand, update_brand, add_network
      strategy_service.py          # generate_strategy() — calls Claude API
    core/
      security.py                  # hash_password, verify_password, create_jwt, decode_jwt
      dependencies.py              # get_db, get_current_user, require_role
  tests/
    conftest.py                    # test DB, test client, fixtures
    test_auth.py
    test_workspaces.py
    test_brands.py
    test_strategy.py
  alembic/
    env.py
    versions/                      # Migration files (auto-generated)
  requirements.txt
  Dockerfile
  .env.example
```

### Frontend

```
frontend/
  src/
    app/
      (auth)/
        login/page.tsx
        register/page.tsx
        layout.tsx                 # Unauthenticated layout
      (dashboard)/
        layout.tsx                 # Sidebar + top nav shell
        page.tsx                   # Dashboard home (redirect to onboarding if no brand)
        onboarding/
          page.tsx                 # Multi-step onboarding wizard
        brand/
          page.tsx                 # Brand profile view/edit
        strategy/
          page.tsx                 # Content pillars + content plan calendar view
    components/
      auth/
        LoginForm.tsx
        RegisterForm.tsx
      onboarding/
        OnboardingWizard.tsx       # Step controller
        steps/
          StepCompanyType.tsx
          StepBrandProfile.tsx
          StepNetworks.tsx
          StepGoals.tsx
          StepTone.tsx
      strategy/
        ContentPillars.tsx
        ContentCalendar.tsx
      ui/                          # shadcn/ui components (generated, not hand-written)
    lib/
      api.ts                       # Typed fetch wrapper, base URL from env
      auth.ts                      # Token storage, refresh logic
      validations/
        auth.ts                    # Zod schemas for auth forms
        brand.ts                   # Zod schemas for brand forms
    store/
      auth.ts                      # Zustand: current user, token
      workspace.ts                 # Zustand: current workspace
    types/
      api.ts                       # Mirror of backend schemas
  package.json
  tsconfig.json
  tailwind.config.ts
  next.config.ts
  Dockerfile
```

### Infrastructure

```
docker-compose.yml                 # api, worker (stub), postgres, redis, nginx
nginx.conf
.env.example
.gitignore
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/requirements.txt`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`
- Create: `backend/.env.example`
- Create: `frontend/package.json` (via Next.js CLI)
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Create root directory structure**

```bash
mkdir -p backend/app/{models,schemas,api/v1,services,core}
mkdir -p backend/tests
mkdir -p backend/alembic/versions
touch backend/app/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/v1/__init__.py
touch backend/app/services/__init__.py
touch backend/app/core/__init__.py
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```text
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
httpx==0.27.2
```

- [ ] **Step 3: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    anthropic_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 4: Create `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router

app = FastAPI(title="Social Content Factory", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create `backend/app/api/v1/router.py`**

```python
from fastapi import APIRouter
from app.api.v1 import auth, workspaces, brands, strategy

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(brands.router, prefix="/brands", tags=["brands"])
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
```

- [ ] **Step 7: Create `backend/.env.example`**

```env
DATABASE_URL=postgresql://scf:scf@localhost:5432/scf
SECRET_KEY=change-me-to-a-random-secret-32-chars
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 8: Create `docker-compose.yml`**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: scf
      POSTGRES_PASSWORD: scf
      POSTGRES_DB: scf
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

- [ ] **Step 9: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

- [ ] **Step 10: Scaffold Next.js frontend**

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --src-dir --no-git --import-alias "@/*"
```

- [ ] **Step 11: Install frontend dependencies**

```bash
cd frontend
npm install zustand react-hook-form @hookform/resolvers zod axios
npx shadcn@latest init
# Choose: Default style, Slate color, CSS variables yes
npx shadcn@latest add button input label card form select checkbox badge
```

- [ ] **Step 12: Create `frontend/src/lib/api.ts`**

```typescript
import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;
```

- [ ] **Step 13: Verify services start**

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with real values
docker compose up postgres redis -d
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload
# Expected: Uvicorn running on http://127.0.0.1:8000
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

- [ ] **Step 14: Commit**

```bash
git init
git add .
git commit -m "feat: project scaffolding — FastAPI + Next.js + Docker Compose"
```

---

## Task 2: Database Models

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/workspace.py`
- Create: `backend/app/models/brand.py`
- Create: `backend/app/models/strategy.py`
- Create: `backend/alembic/env.py`

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class UserRole(str, enum.Enum):
    owner = "owner"
    editor = "editor"
    approver = "approver"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["WorkspaceMember"]] = relationship(back_populates="user")
```

- [ ] **Step 2: Create `backend/app/models/workspace.py`**

```python
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.user import UserRole

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace")
    brand: Mapped["Brand"] = relationship(back_populates="workspace", uselist=False)

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
```

- [ ] **Step 3: Create `backend/app/models/brand.py`**

```python
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class NetworkType(str, enum.Enum):
    instagram = "instagram"
    vk = "vk"
    telegram = "telegram"

class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False)
    goals: Mapped[list] = mapped_column(JSON, default=list)
    tone_of_voice: Mapped[str] = mapped_column(String(100), nullable=False)
    posting_frequency: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="brand")
    social_accounts: Mapped[list["SocialAccount"]] = relationship(back_populates="brand")
    pillars: Mapped[list["ContentPillar"]] = relationship(back_populates="brand")
    plan_items: Mapped[list["ContentPlanItem"]] = relationship(back_populates="brand")

class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    network: Mapped[NetworkType] = mapped_column(Enum(NetworkType), nullable=False)
    handle: Mapped[str] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)

    brand: Mapped["Brand"] = relationship(back_populates="social_accounts")
```

- [ ] **Step 4: Create `backend/app/models/strategy.py`**

```python
import enum
from datetime import datetime, date
from sqlalchemy import String, Text, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class FunnelStage(str, enum.Enum):
    tofu = "tofu"
    mofu = "mofu"
    bofu = "bofu"
    retention = "retention"

class ContentPillar(Base):
    __tablename__ = "content_pillars"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    funnel_stages: Mapped[str] = mapped_column(String(255), nullable=False)  # comma-separated
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="pillars")

class ContentPlanItem(Base):
    __tablename__ = "content_plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    pillar_id: Mapped[int] = mapped_column(ForeignKey("content_pillars.id"), nullable=True)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(100), nullable=False)
    funnel_stage: Mapped[FunnelStage] = mapped_column(Enum(FunnelStage), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="plan_items")
    pillar: Mapped["ContentPillar"] = relationship()
```

- [ ] **Step 5: Update `backend/app/models/__init__.py`**

```python
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember
from app.models.brand import Brand, SocialAccount, NetworkType
from app.models.strategy import ContentPillar, ContentPlanItem, FunnelStage
```

- [ ] **Step 6: Initialize Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 7: Update `backend/alembic/env.py`** — replace the `target_metadata` section

```python
# At top of env.py, add these imports after existing ones:
import sys
sys.path.insert(0, "/app")

from app.database import Base
from app.models import *  # noqa: F401, F403 — ensures all models are registered

# Change this line:
target_metadata = Base.metadata
```

- [ ] **Step 8: Update `backend/alembic.ini`** — set sqlalchemy.url

```ini
# Change this line:
sqlalchemy.url = postgresql://scf:scf@localhost:5432/scf
```

- [ ] **Step 9: Generate and run migration**

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
# Expected: tables created in postgres
```

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/ backend/alembic/
git commit -m "feat: database models — user, workspace, brand, strategy"
```

---

## Task 3: Auth — Core Security + Register/Login

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/dependencies.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/v1/auth.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

TEST_DATABASE_URL = "postgresql://scf:scf@localhost:5432/scf_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

Create `backend/tests/test_auth.py`:

```python
def test_register_success(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "strongpass123",
        "full_name": "Test User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "access_token" not in data  # register does not return token

def test_register_duplicate_email(client):
    payload = {"email": "test@example.com", "password": "pass123", "full_name": "User"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409

def test_login_success(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com", "password": "pass123", "full_name": "User"
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com", "password": "pass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com", "password": "pass123", "full_name": "User"
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com", "password": "wrong"
    })
    assert response.status_code == 401

def test_get_me(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com", "password": "pass123", "full_name": "User"
    })
    login = client.post("/api/v1/auth/login", json={
        "email": "test@example.com", "password": "pass123"
    })
    token = login.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend
# create test DB first
createdb scf_test  # or: psql -U scf -c "CREATE DATABASE scf_test"
pytest tests/test_auth.py -v
# Expected: ImportError or 404 — endpoints don't exist yet
```

- [ ] **Step 3: Create `backend/app/core/security.py`**

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> int:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return int(payload["sub"])
```

- [ ] **Step 4: Create `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Create `backend/app/services/auth_service.py`**

```python
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token

def create_user(db: Session, email: str, password: str, full_name: str) -> User:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email, hashed_password=hash_password(password), full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate(db: Session, email: str, password: str) -> str:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return create_access_token(user.id)
```

- [ ] **Step 6: Create `backend/app/core/dependencies.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.database import get_db
from app.models.user import User, UserRole
from app.models.workspace import WorkspaceMember
from app.core.security import decode_token

bearer = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
) -> User:
    try:
        user_id = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(*roles: UserRole):
    def dependency(
        workspace_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> WorkspaceMember:
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id
        ).first()
        if not member or member.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return member
    return dependency
```

- [ ] **Step 7: Create `backend/app/api/v1/auth.py`**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.services.auth_service import create_user, authenticate
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return create_user(db, payload.email, payload.password, payload.full_name)

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token = authenticate(db, payload.email, payload.password)
    return {"access_token": token}

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 8: Run tests — verify they pass**

```bash
cd backend
pytest tests/test_auth.py -v
# Expected: 5 tests PASSED
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/core/ backend/app/schemas/auth.py backend/app/services/auth_service.py backend/app/api/v1/auth.py backend/tests/
git commit -m "feat: auth — register, login, JWT, get_current_user"
```

---

## Task 4: Workspace Management

**Files:**
- Create: `backend/app/schemas/workspace.py`
- Create: `backend/app/services/workspace_service.py`
- Create: `backend/app/api/v1/workspaces.py`
- Create: `backend/tests/test_workspaces.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_workspaces.py`:

```python
import pytest

@pytest.fixture()
def auth_client(client):
    """Returns client with Authorization header for a registered user."""
    client.post("/api/v1/auth/register", json={
        "email": "owner@example.com", "password": "pass123", "full_name": "Owner"
    })
    resp = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "pass123"})
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client

def test_create_workspace(auth_client):
    response = auth_client.post("/api/v1/workspaces/", json={"name": "My Agency"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Agency"
    assert data["my_role"] == "owner"

def test_list_workspaces(auth_client):
    auth_client.post("/api/v1/workspaces/", json={"name": "WS1"})
    auth_client.post("/api/v1/workspaces/", json={"name": "WS2"})
    response = auth_client.get("/api/v1/workspaces/")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_invite_member(auth_client, client):
    # Register second user
    client.post("/api/v1/auth/register", json={
        "email": "editor@example.com", "password": "pass123", "full_name": "Editor"
    })
    ws = auth_client.post("/api/v1/workspaces/", json={"name": "Team WS"}).json()
    response = auth_client.post(f"/api/v1/workspaces/{ws['id']}/members", json={
        "email": "editor@example.com", "role": "editor"
    })
    assert response.status_code == 201
    assert response.json()["role"] == "editor"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_workspaces.py -v
# Expected: FAILED — endpoints don't exist
```

- [ ] **Step 3: Create `backend/app/schemas/workspace.py`**

```python
from pydantic import BaseModel
from app.models.user import UserRole

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceOut(BaseModel):
    id: int
    name: str
    my_role: UserRole

    model_config = {"from_attributes": True}

class InviteMemberRequest(BaseModel):
    email: str
    role: UserRole

class MemberOut(BaseModel):
    id: int
    user_id: int
    role: UserRole
    full_name: str
    email: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Create `backend/app/services/workspace_service.py`**

```python
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User, UserRole

def create_workspace(db: Session, name: str, owner_id: int) -> tuple[Workspace, WorkspaceMember]:
    workspace = Workspace(name=name)
    db.add(workspace)
    db.flush()
    member = WorkspaceMember(workspace_id=workspace.id, user_id=owner_id, role=UserRole.owner)
    db.add(member)
    db.commit()
    db.refresh(workspace)
    return workspace, member

def list_workspaces(db: Session, user_id: int) -> list[tuple[Workspace, WorkspaceMember]]:
    members = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    return [(m.workspace, m) for m in members]

def add_member(db: Session, workspace_id: int, email: str, role: UserRole) -> WorkspaceMember:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already a member")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
```

- [ ] **Step 5: Create `backend/app/api/v1/workspaces.py`**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.workspace import WorkspaceCreate, WorkspaceOut, InviteMemberRequest, MemberOut
from app.services.workspace_service import create_workspace, list_workspaces, add_member
from app.core.dependencies import get_current_user, require_role

router = APIRouter()

@router.post("/", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create(payload: WorkspaceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, member = create_workspace(db, payload.name, current_user.id)
    return WorkspaceOut(id=workspace.id, name=workspace.name, my_role=member.role)

@router.get("/", response_model=list[WorkspaceOut])
def list_all(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pairs = list_workspaces(db, current_user.id)
    return [WorkspaceOut(id=ws.id, name=ws.name, my_role=m.role) for ws, m in pairs]

@router.post("/{workspace_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def invite(
    workspace_id: int,
    payload: InviteMemberRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner))
):
    member = add_member(db, workspace_id, payload.email, payload.role)
    return MemberOut(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        full_name=member.user.full_name,
        email=member.user.email
    )
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
pytest tests/test_workspaces.py -v
# Expected: 3 tests PASSED
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/workspace.py backend/app/services/workspace_service.py backend/app/api/v1/workspaces.py backend/tests/test_workspaces.py
git commit -m "feat: workspace management — create, list, invite members with roles"
```

---

## Task 5: Brand Profile API

**Files:**
- Create: `backend/app/schemas/brand.py`
- Create: `backend/app/services/brand_service.py`
- Create: `backend/app/api/v1/brands.py`
- Create: `backend/tests/test_brands.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_brands.py`:

```python
import pytest

@pytest.fixture()
def owner_client(client):
    client.post("/api/v1/auth/register", json={"email": "o@x.com", "password": "p", "full_name": "O"})
    token = client.post("/api/v1/auth/login", json={"email": "o@x.com", "password": "p"}).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}).json()
    return client, ws["id"]

BRAND_PAYLOAD = {
    "name": "Acme Corp",
    "company_type": "ecommerce",
    "description": "We sell widgets",
    "target_audience": "SMBs in Russia",
    "goals": ["increase_brand_awareness", "generate_leads"],
    "tone_of_voice": "professional",
    "posting_frequency": "daily",
    "networks": ["instagram", "vk", "telegram"]
}

def test_create_brand(owner_client):
    client, ws_id = owner_client
    response = client.post(f"/api/v1/workspaces/{ws_id}/brand", json=BRAND_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert len(data["social_accounts"]) == 3

def test_get_brand(owner_client):
    client, ws_id = owner_client
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json=BRAND_PAYLOAD)
    response = client.get(f"/api/v1/workspaces/{ws_id}/brand")
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"

def test_update_brand(owner_client):
    client, ws_id = owner_client
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json=BRAND_PAYLOAD)
    response = client.patch(f"/api/v1/workspaces/{ws_id}/brand", json={"tone_of_voice": "casual"})
    assert response.status_code == 200
    assert response.json()["tone_of_voice"] == "casual"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_brands.py -v
# Expected: FAILED — endpoints don't exist
```

- [ ] **Step 3: Create `backend/app/schemas/brand.py`**

```python
from pydantic import BaseModel
from app.models.brand import NetworkType

class NetworkOut(BaseModel):
    id: int
    network: NetworkType
    handle: str | None
    enabled: bool
    model_config = {"from_attributes": True}

class BrandCreate(BaseModel):
    name: str
    company_type: str
    description: str
    target_audience: str
    goals: list[str]
    tone_of_voice: str
    posting_frequency: str
    networks: list[NetworkType]

class BrandUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_audience: str | None = None
    goals: list[str] | None = None
    tone_of_voice: str | None = None
    posting_frequency: str | None = None

class BrandOut(BaseModel):
    id: int
    name: str
    company_type: str
    description: str
    target_audience: str
    goals: list[str]
    tone_of_voice: str
    posting_frequency: str
    social_accounts: list[NetworkOut]
    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Create `backend/app/services/brand_service.py`**

```python
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.brand import Brand, SocialAccount, NetworkType
from app.schemas.brand import BrandCreate, BrandUpdate

def create_brand(db: Session, workspace_id: int, payload: BrandCreate) -> Brand:
    if db.query(Brand).filter(Brand.workspace_id == workspace_id).first():
        raise HTTPException(status_code=409, detail="Brand already exists for this workspace")
    brand = Brand(
        workspace_id=workspace_id,
        name=payload.name,
        company_type=payload.company_type,
        description=payload.description,
        target_audience=payload.target_audience,
        goals=payload.goals,
        tone_of_voice=payload.tone_of_voice,
        posting_frequency=payload.posting_frequency,
    )
    db.add(brand)
    db.flush()
    for network in payload.networks:
        db.add(SocialAccount(brand_id=brand.id, network=network))
    db.commit()
    db.refresh(brand)
    return brand

def get_brand(db: Session, workspace_id: int) -> Brand:
    brand = db.query(Brand).filter(Brand.workspace_id == workspace_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand

def update_brand(db: Session, workspace_id: int, payload: BrandUpdate) -> Brand:
    brand = get_brand(db, workspace_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(brand, field, value)
    db.commit()
    db.refresh(brand)
    return brand
```

- [ ] **Step 5: Create `backend/app/api/v1/brands.py`**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserRole
from app.schemas.brand import BrandCreate, BrandUpdate, BrandOut
from app.services.brand_service import create_brand, get_brand, update_brand
from app.core.dependencies import require_role

router = APIRouter()

@router.post("/workspaces/{workspace_id}/brand", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
def create(
    workspace_id: int,
    payload: BrandCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor))
):
    return create_brand(db, workspace_id, payload)

@router.get("/workspaces/{workspace_id}/brand", response_model=BrandOut)
def get(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor, UserRole.approver))
):
    return get_brand(db, workspace_id)

@router.patch("/workspaces/{workspace_id}/brand", response_model=BrandOut)
def update(
    workspace_id: int,
    payload: BrandUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor))
):
    return update_brand(db, workspace_id, payload)
```

- [ ] **Step 6: Register brand router in `backend/app/api/v1/router.py`**

```python
from fastapi import APIRouter
from app.api.v1 import auth, workspaces, brands, strategy

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(brands.router, tags=["brands"])  # prefix is inside the router
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
```

- [ ] **Step 7: Run tests — verify they pass**

```bash
pytest tests/test_brands.py -v
# Expected: 3 tests PASSED
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/brand.py backend/app/services/brand_service.py backend/app/api/v1/brands.py backend/tests/test_brands.py backend/app/api/v1/router.py
git commit -m "feat: brand profile API — create, get, update with social accounts"
```

---

## Task 6: Strategy Engine (Claude API)

**Files:**
- Create: `backend/app/schemas/strategy.py`
- Create: `backend/app/services/strategy_service.py`
- Create: `backend/app/api/v1/strategy.py`
- Create: `backend/tests/test_strategy.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_strategy.py`:

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture()
def workspace_with_brand(client):
    client.post("/api/v1/auth/register", json={"email": "o@x.com", "password": "p", "full_name": "O"})
    token = client.post("/api/v1/auth/login", json={"email": "o@x.com", "password": "p"}).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}).json()
    ws_id = ws["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json={
        "name": "Acme", "company_type": "ecommerce", "description": "Sell widgets",
        "target_audience": "SMBs", "goals": ["leads"], "tone_of_voice": "professional",
        "posting_frequency": "daily", "networks": ["instagram", "vk"]
    })
    return client, ws_id

MOCK_STRATEGY = {
    "pillars": [
        {"title": "Education", "description": "Teach audience", "funnel_stages": "tofu,mofu"},
        {"title": "Cases", "description": "Show results", "funnel_stages": "mofu,bofu"},
    ],
    "plan_items": [
        {"network": "instagram", "format": "reels", "funnel_stage": "tofu",
         "topic": "5 tips for widgets", "planned_date": "2026-04-15", "pillar_index": 0},
    ]
}

def test_generate_strategy(workspace_with_brand):
    client, ws_id = workspace_with_brand
    with patch("app.services.strategy_service.call_claude", return_value=MOCK_STRATEGY):
        response = client.post(f"/api/v1/strategy/workspaces/{ws_id}/generate")
    assert response.status_code == 200
    data = response.json()
    assert len(data["pillars"]) == 2
    assert len(data["plan_items"]) >= 1

def test_get_pillars(workspace_with_brand):
    client, ws_id = workspace_with_brand
    with patch("app.services.strategy_service.call_claude", return_value=MOCK_STRATEGY):
        client.post(f"/api/v1/strategy/workspaces/{ws_id}/generate")
    response = client.get(f"/api/v1/strategy/workspaces/{ws_id}/pillars")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_get_plan(workspace_with_brand):
    client, ws_id = workspace_with_brand
    with patch("app.services.strategy_service.call_claude", return_value=MOCK_STRATEGY):
        client.post(f"/api/v1/strategy/workspaces/{ws_id}/generate")
    response = client.get(f"/api/v1/strategy/workspaces/{ws_id}/plan")
    assert response.status_code == 200
    assert len(response.json()) >= 1
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_strategy.py -v
# Expected: FAILED — endpoints don't exist
```

- [ ] **Step 3: Create `backend/app/schemas/strategy.py`**

```python
from pydantic import BaseModel
from datetime import date
from app.models.strategy import FunnelStage

class PillarOut(BaseModel):
    id: int
    title: str
    description: str
    funnel_stages: str
    model_config = {"from_attributes": True}

class ContentPlanItemOut(BaseModel):
    id: int
    network: str
    format: str
    funnel_stage: FunnelStage
    topic: str
    planned_date: date
    model_config = {"from_attributes": True}

class StrategyOut(BaseModel):
    pillars: list[PillarOut]
    plan_items: list[ContentPlanItemOut]
```

- [ ] **Step 4: Create `backend/app/services/strategy_service.py`**

```python
import json
from anthropic import Anthropic
from sqlalchemy.orm import Session
from app.config import settings
from app.models.brand import Brand
from app.models.strategy import ContentPillar, ContentPlanItem, FunnelStage
from app.services.brand_service import get_brand

client_anthropic = Anthropic(api_key=settings.anthropic_api_key)

def call_claude(prompt: str) -> dict:
    """Call Claude API and parse JSON response."""
    message = client_anthropic.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text
    # Extract JSON from response
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])

def build_strategy_prompt(brand: Brand) -> str:
    from datetime import date, timedelta
    today = date.today()
    # Start from next Monday
    days_until_monday = (7 - today.weekday()) % 7 or 7
    start = today + timedelta(days=days_until_monday)
    end = start + timedelta(weeks=4) - timedelta(days=1)

    networks = [a.network.value for a in brand.social_accounts if a.enabled]
    return f"""You are an expert social media strategist for Russian-market brands.

Brand: {brand.name}
Type: {brand.company_type}
Description: {brand.description}
Target audience: {brand.target_audience}
Goals: {', '.join(brand.goals)}
Tone of voice: {brand.tone_of_voice}
Posting frequency: {brand.posting_frequency}
Active networks: {', '.join(networks)}

Generate a content strategy in JSON format with this exact structure:
{{
  "pillars": [
    {{"title": "...", "description": "...", "funnel_stages": "tofu,mofu"}}
  ],
  "plan_items": [
    {{
      "network": "instagram",
      "format": "reels",
      "funnel_stage": "tofu",
      "topic": "...",
      "planned_date": "{start.isoformat()}",
      "pillar_index": 0
    }}
  ]
}}

Rules:
- Create 4-6 content pillars covering all funnel stages (tofu, mofu, bofu, retention)
- Create 28 plan items (4 weeks of content) distributed across selected networks
- Format must match network: instagram uses reels/carousel/static_post/story, vk uses clip/post/poll/long_video, telegram uses longread/voice/image_post/poll/link
- Balance funnel stages: ~40% tofu, 30% mofu, 20% bofu, 10% retention
- No more than 2 bofu posts per week
- All dates from {start.isoformat()} to {end.isoformat()}
- Respond ONLY with valid JSON, no explanation
"""

def generate_strategy(db: Session, workspace_id: int) -> dict:
    brand = get_brand(db, workspace_id)

    # Clear old strategy
    db.query(ContentPlanItem).filter(ContentPlanItem.brand_id == brand.id).delete()
    db.query(ContentPillar).filter(ContentPillar.brand_id == brand.id).delete()
    db.commit()

    prompt = build_strategy_prompt(brand)
    data = call_claude(prompt)

    pillars = []
    for p in data["pillars"]:
        pillar = ContentPillar(
            brand_id=brand.id,
            title=p["title"],
            description=p["description"],
            funnel_stages=p["funnel_stages"]
        )
        db.add(pillar)
        pillars.append(pillar)
    db.flush()

    for item in data["plan_items"]:
        pillar_id = pillars[item["pillar_index"]].id if item.get("pillar_index") is not None else None
        db.add(ContentPlanItem(
            brand_id=brand.id,
            pillar_id=pillar_id,
            network=item["network"],
            format=item["format"],
            funnel_stage=FunnelStage(item["funnel_stage"]),
            topic=item["topic"],
            planned_date=item["planned_date"]
        ))

    db.commit()

    pillars_out = db.query(ContentPillar).filter(ContentPillar.brand_id == brand.id).all()
    items_out = db.query(ContentPlanItem).filter(ContentPlanItem.brand_id == brand.id).all()
    return {"pillars": pillars_out, "plan_items": items_out}
```

- [ ] **Step 5: Create `backend/app/api/v1/strategy.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserRole
from app.schemas.strategy import PillarOut, ContentPlanItemOut, StrategyOut
from app.services.strategy_service import generate_strategy
from app.services.brand_service import get_brand
from app.models.strategy import ContentPillar, ContentPlanItem
from app.core.dependencies import require_role

router = APIRouter()

@router.post("/workspaces/{workspace_id}/generate", response_model=StrategyOut)
def generate(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner))
):
    return generate_strategy(db, workspace_id)

@router.get("/workspaces/{workspace_id}/pillars", response_model=list[PillarOut])
def get_pillars(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor, UserRole.approver))
):
    brand = get_brand(db, workspace_id)
    return db.query(ContentPillar).filter(ContentPillar.brand_id == brand.id).all()

@router.get("/workspaces/{workspace_id}/plan", response_model=list[ContentPlanItemOut])
def get_plan(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor, UserRole.approver))
):
    brand = get_brand(db, workspace_id)
    return db.query(ContentPlanItem).filter(ContentPlanItem.brand_id == brand.id)\
        .order_by(ContentPlanItem.planned_date).all()
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
pytest tests/test_strategy.py -v
# Expected: 3 tests PASSED (Claude is mocked)
```

- [ ] **Step 7: Run all tests**

```bash
pytest tests/ -v
# Expected: all 11 tests PASSED
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/strategy.py backend/app/services/strategy_service.py backend/app/api/v1/strategy.py backend/tests/test_strategy.py
git commit -m "feat: strategy engine — Claude API generates pillars and 4-week content plan"
```

---

## Task 7: Frontend Auth Pages

**Files:**
- Create: `frontend/src/store/auth.ts`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/lib/validations/auth.ts`
- Create: `frontend/src/components/auth/LoginForm.tsx`
- Create: `frontend/src/components/auth/RegisterForm.tsx`
- Create: `frontend/src/app/(auth)/layout.tsx`
- Create: `frontend/src/app/(auth)/login/page.tsx`
- Create: `frontend/src/app/(auth)/register/page.tsx`

- [ ] **Step 1: Create `frontend/src/types/api.ts`**

```typescript
export interface User {
  id: number;
  email: string;
  full_name: string;
}

export interface Workspace {
  id: number;
  name: string;
  my_role: "owner" | "editor" | "approver";
}

export interface Brand {
  id: number;
  name: string;
  company_type: string;
  description: string;
  target_audience: string;
  goals: string[];
  tone_of_voice: string;
  posting_frequency: string;
  social_accounts: SocialAccount[];
}

export interface SocialAccount {
  id: number;
  network: "instagram" | "vk" | "telegram";
  handle: string | null;
  enabled: boolean;
}

export interface ContentPillar {
  id: number;
  title: string;
  description: string;
  funnel_stages: string;
}

export interface ContentPlanItem {
  id: number;
  network: string;
  format: string;
  funnel_stage: "tofu" | "mofu" | "bofu" | "retention";
  topic: string;
  planned_date: string;
}
```

- [ ] **Step 2: Create `frontend/src/store/auth.ts`**

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User } from "@/types/api";

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => {
        localStorage.setItem("access_token", token);
        set({ user, token });
      },
      clearAuth: () => {
        localStorage.removeItem("access_token");
        set({ user: null, token: null });
      },
    }),
    { name: "auth-storage" }
  )
);
```

- [ ] **Step 3: Create `frontend/src/lib/validations/auth.ts`**

```typescript
import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Введите корректный email"),
  password: z.string().min(1, "Введите пароль"),
});

export const registerSchema = z.object({
  full_name: z.string().min(2, "Введите имя"),
  email: z.string().email("Введите корректный email"),
  password: z.string().min(6, "Пароль минимум 6 символов"),
});

export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
```

- [ ] **Step 4: Create `frontend/src/components/auth/LoginForm.tsx`**

```tsx
"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { loginSchema, LoginInput } from "@/lib/validations/auth";
import { useAuthStore } from "@/store/auth";
import api from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginInput) => {
    try {
      const tokenRes = await api.post("/auth/login", data);
      const token = tokenRes.data.access_token;
      const userRes = await api.get("/auth/me", { headers: { Authorization: `Bearer ${token}` } });
      setAuth(userRes.data, token);
      router.push("/");
    } catch {
      setError("root", { message: "Неверный email или пароль" });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" {...register("email")} />
        {errors.email && <p className="text-sm text-red-500 mt-1">{errors.email.message}</p>}
      </div>
      <div>
        <Label htmlFor="password">Пароль</Label>
        <Input id="password" type="password" {...register("password")} />
        {errors.password && <p className="text-sm text-red-500 mt-1">{errors.password.message}</p>}
      </div>
      {errors.root && <p className="text-sm text-red-500">{errors.root.message}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Входим..." : "Войти"}
      </Button>
    </form>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/auth/RegisterForm.tsx`**

```tsx
"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { registerSchema, RegisterInput } from "@/lib/validations/auth";
import api from "@/lib/api";

export function RegisterForm() {
  const router = useRouter();
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterInput) => {
    try {
      await api.post("/auth/register", data);
      router.push("/login?registered=1");
    } catch (err: any) {
      const msg = err.response?.status === 409 ? "Email уже зарегистрирован" : "Ошибка регистрации";
      setError("root", { message: msg });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Label htmlFor="full_name">Имя</Label>
        <Input id="full_name" {...register("full_name")} />
        {errors.full_name && <p className="text-sm text-red-500 mt-1">{errors.full_name.message}</p>}
      </div>
      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" {...register("email")} />
        {errors.email && <p className="text-sm text-red-500 mt-1">{errors.email.message}</p>}
      </div>
      <div>
        <Label htmlFor="password">Пароль</Label>
        <Input id="password" type="password" {...register("password")} />
        {errors.password && <p className="text-sm text-red-500 mt-1">{errors.password.message}</p>}
      </div>
      {errors.root && <p className="text-sm text-red-500">{errors.root.message}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Регистрируем..." : "Создать аккаунт"}
      </Button>
    </form>
  );
}
```

- [ ] **Step 6: Create `frontend/src/app/(auth)/layout.tsx`**

```tsx
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-sky-400">⚡ Social Content Factory</h1>
          <p className="text-slate-400 mt-1 text-sm">Автоматизация SMM для вашего бизнеса</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Create `frontend/src/app/(auth)/login/page.tsx`**

```tsx
import Link from "next/link";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-100 mb-6">Войти в аккаунт</h2>
      <LoginForm />
      <p className="text-sm text-slate-400 mt-4 text-center">
        Нет аккаунта?{" "}
        <Link href="/register" className="text-sky-400 hover:underline">Зарегистрироваться</Link>
      </p>
    </>
  );
}
```

- [ ] **Step 8: Create `frontend/src/app/(auth)/register/page.tsx`**

```tsx
import Link from "next/link";
import { RegisterForm } from "@/components/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-100 mb-6">Создать аккаунт</h2>
      <RegisterForm />
      <p className="text-sm text-slate-400 mt-4 text-center">
        Уже есть аккаунт?{" "}
        <Link href="/login" className="text-sky-400 hover:underline">Войти</Link>
      </p>
    </>
  );
}
```

- [ ] **Step 9: Verify manually**

```bash
cd frontend && npm run dev
# Open http://localhost:3000/register
# Register a user → should redirect to /login?registered=1
# Login → should redirect to /
```

- [ ] **Step 10: Commit**

```bash
git add frontend/src/
git commit -m "feat: auth UI — login and register pages with form validation"
```

---

## Task 8: Onboarding Wizard (Frontend)

**Files:**
- Create: `frontend/src/store/workspace.ts`
- Create: `frontend/src/components/onboarding/OnboardingWizard.tsx`
- Create: `frontend/src/components/onboarding/steps/StepCompanyType.tsx`
- Create: `frontend/src/components/onboarding/steps/StepBrandProfile.tsx`
- Create: `frontend/src/components/onboarding/steps/StepNetworks.tsx`
- Create: `frontend/src/components/onboarding/steps/StepGoals.tsx`
- Create: `frontend/src/components/onboarding/steps/StepTone.tsx`
- Create: `frontend/src/app/(dashboard)/onboarding/page.tsx`

- [ ] **Step 1: Create `frontend/src/store/workspace.ts`**

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Workspace } from "@/types/api";

interface WorkspaceState {
  current: Workspace | null;
  setCurrent: (ws: Workspace) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      current: null,
      setCurrent: (ws) => set({ current: ws }),
    }),
    { name: "workspace-storage" }
  )
);
```

- [ ] **Step 2: Create `frontend/src/components/onboarding/OnboardingWizard.tsx`**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { StepCompanyType } from "./steps/StepCompanyType";
import { StepBrandProfile } from "./steps/StepBrandProfile";
import { StepNetworks } from "./steps/StepNetworks";
import { StepGoals } from "./steps/StepGoals";
import { StepTone } from "./steps/StepTone";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspace";

export interface OnboardingData {
  workspaceName: string;
  company_type: string;
  name: string;
  description: string;
  target_audience: string;
  networks: string[];
  goals: string[];
  tone_of_voice: string;
  posting_frequency: string;
}

const STEPS = ["Компания", "Бренд", "Соцсети", "Цели", "Тон"];

export function OnboardingWizard() {
  const router = useRouter();
  const setCurrent = useWorkspaceStore((s) => s.setCurrent);
  const [step, setStep] = useState(0);
  const [data, setData] = useState<Partial<OnboardingData>>({});
  const [loading, setLoading] = useState(false);

  const next = (patch: Partial<OnboardingData>) => {
    const updated = { ...data, ...patch };
    setData(updated);
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      submit(updated as OnboardingData);
    }
  };

  const submit = async (final: OnboardingData) => {
    setLoading(true);
    try {
      const ws = await api.post("/workspaces/", { name: final.workspaceName });
      const wsId = ws.data.id;
      setCurrent(ws.data);
      await api.post(`/workspaces/${wsId}/brand`, {
        name: final.name,
        company_type: final.company_type,
        description: final.description,
        target_audience: final.target_audience,
        goals: final.goals,
        tone_of_voice: final.tone_of_voice,
        posting_frequency: final.posting_frequency,
        networks: final.networks,
      });
      router.push("/strategy");
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              i < step ? "bg-sky-500 text-white" : i === step ? "bg-sky-400 text-slate-950" : "bg-slate-800 text-slate-400"
            }`}>{i + 1}</div>
            <span className={`text-sm ${i === step ? "text-slate-100" : "text-slate-500"}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="flex-1 h-px bg-slate-800 mx-2" />}
          </div>
        ))}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
        {step === 0 && <StepCompanyType onNext={next} />}
        {step === 1 && <StepBrandProfile onNext={next} />}
        {step === 2 && <StepNetworks onNext={next} />}
        {step === 3 && <StepGoals onNext={next} />}
        {step === 4 && <StepTone onNext={next} loading={loading} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/onboarding/steps/StepCompanyType.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const COMPANY_TYPES = [
  { value: "ecommerce", label: "Интернет-магазин" },
  { value: "services", label: "Услуги" },
  { value: "agency", label: "Агентство" },
  { value: "personal_brand", label: "Личный бренд" },
  { value: "saas", label: "SaaS / IT" },
  { value: "other", label: "Другое" },
];

export function StepCompanyType({ onNext }: { onNext: (data: any) => void }) {
  const [selected, setSelected] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Тип компании</h2>
      <p className="text-slate-400 text-sm mb-6">Это поможет агенту выбрать правильную стратегию</p>

      <div className="mb-6">
        <Label>Название воркспейса</Label>
        <Input
          className="mt-1"
          placeholder="Например: Моё агентство"
          value={workspaceName}
          onChange={(e) => setWorkspaceName(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-8">
        {COMPANY_TYPES.map((t) => (
          <button
            key={t.value}
            onClick={() => setSelected(t.value)}
            className={`p-4 rounded-lg border text-left text-sm transition-all ${
              selected === t.value
                ? "border-sky-500 bg-sky-500/10 text-sky-400"
                : "border-slate-700 text-slate-300 hover:border-slate-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <Button
        className="w-full"
        disabled={!selected || !workspaceName.trim()}
        onClick={() => onNext({ company_type: selected, workspaceName: workspaceName.trim() })}
      >
        Далее →
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/onboarding/steps/StepBrandProfile.tsx`**

```tsx
"use client";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function StepBrandProfile({ onNext }: { onNext: (data: any) => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm();

  return (
    <form onSubmit={handleSubmit(onNext)}>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Профиль бренда</h2>
      <p className="text-slate-400 text-sm mb-6">Агент использует это для создания контента</p>

      <div className="space-y-4">
        <div>
          <Label>Название бренда</Label>
          <Input className="mt-1" {...register("name", { required: true })} placeholder="Acme Corp" />
        </div>
        <div>
          <Label>Описание бизнеса</Label>
          <textarea
            {...register("description", { required: true })}
            className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-md p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 resize-none"
            rows={3}
            placeholder="Чем занимается компания, что продаёт, в чём уникальность..."
          />
        </div>
        <div>
          <Label>Целевая аудитория</Label>
          <textarea
            {...register("target_audience", { required: true })}
            className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-md p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 resize-none"
            rows={2}
            placeholder="Кто ваш клиент: возраст, интересы, боли, география..."
          />
        </div>
      </div>

      <Button type="submit" className="w-full mt-6">Далее →</Button>
    </form>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/onboarding/steps/StepNetworks.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const NETWORKS = [
  { value: "instagram", label: "Instagram", icon: "📸" },
  { value: "vk", label: "VKontakte", icon: "💙" },
  { value: "telegram", label: "Telegram", icon: "✈️" },
];

export function StepNetworks({ onNext }: { onNext: (data: any) => void }) {
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (v: string) =>
    setSelected((prev) => prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Соцсети</h2>
      <p className="text-slate-400 text-sm mb-6">Выберите где будете публиковать контент</p>

      <div className="space-y-3 mb-8">
        {NETWORKS.map((n) => (
          <button
            key={n.value}
            onClick={() => toggle(n.value)}
            className={`w-full p-4 rounded-lg border text-left flex items-center gap-3 transition-all ${
              selected.includes(n.value)
                ? "border-sky-500 bg-sky-500/10"
                : "border-slate-700 hover:border-slate-500"
            }`}
          >
            <span className="text-2xl">{n.icon}</span>
            <span className={`text-sm font-medium ${selected.includes(n.value) ? "text-sky-400" : "text-slate-300"}`}>
              {n.label}
            </span>
            {selected.includes(n.value) && <span className="ml-auto text-sky-400">✓</span>}
          </button>
        ))}
      </div>

      <Button className="w-full" disabled={selected.length === 0} onClick={() => onNext({ networks: selected })}>
        Далее →
      </Button>
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/src/components/onboarding/steps/StepGoals.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const GOALS = [
  { value: "increase_brand_awareness", label: "Повысить узнаваемость бренда" },
  { value: "generate_leads", label: "Генерировать лиды" },
  { value: "drive_sales", label: "Увеличить продажи" },
  { value: "grow_community", label: "Вырастить сообщество" },
  { value: "establish_expertise", label: "Показать экспертизу" },
  { value: "retain_customers", label: "Удержать клиентов" },
];

export function StepGoals({ onNext }: { onNext: (data: any) => void }) {
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (v: string) =>
    setSelected((prev) => prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Цели</h2>
      <p className="text-slate-400 text-sm mb-6">Выберите одну или несколько целей</p>

      <div className="grid grid-cols-1 gap-3 mb-8">
        {GOALS.map((g) => (
          <button
            key={g.value}
            onClick={() => toggle(g.value)}
            className={`p-3 rounded-lg border text-left text-sm transition-all ${
              selected.includes(g.value)
                ? "border-sky-500 bg-sky-500/10 text-sky-400"
                : "border-slate-700 text-slate-300 hover:border-slate-500"
            }`}
          >
            {selected.includes(g.value) ? "✓ " : "  "}{g.label}
          </button>
        ))}
      </div>

      <Button className="w-full" disabled={selected.length === 0} onClick={() => onNext({ goals: selected })}>
        Далее →
      </Button>
    </div>
  );
}
```

- [ ] **Step 7: Create `frontend/src/components/onboarding/steps/StepTone.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

const TONES = [
  { value: "professional", label: "Профессиональный", desc: "Экспертный, уважительный, без сленга" },
  { value: "casual", label: "Дружелюбный", desc: "Живой, тёплый, как общение с другом" },
  { value: "bold", label: "Смелый", desc: "Провокационный, прямой, запоминающийся" },
  { value: "educational", label: "Образовательный", desc: "Обучающий, структурированный, понятный" },
];

const FREQUENCIES = [
  { value: "daily", label: "Ежедневно" },
  { value: "3x_week", label: "3 раза в неделю" },
  { value: "weekly", label: "Еженедельно" },
];

export function StepTone({ onNext, loading }: { onNext: (data: any) => void; loading: boolean }) {
  const [tone, setTone] = useState("");
  const [freq, setFreq] = useState("");

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100 mb-2">Тон и частота</h2>
      <p className="text-slate-400 text-sm mb-6">Последний шаг — агент готов к работе</p>

      <div className="space-y-3 mb-6">
        {TONES.map((t) => (
          <button
            key={t.value}
            onClick={() => setTone(t.value)}
            className={`w-full p-4 rounded-lg border text-left transition-all ${
              tone === t.value ? "border-sky-500 bg-sky-500/10" : "border-slate-700 hover:border-slate-500"
            }`}
          >
            <div className={`text-sm font-medium ${tone === t.value ? "text-sky-400" : "text-slate-200"}`}>{t.label}</div>
            <div className="text-xs text-slate-400 mt-0.5">{t.desc}</div>
          </button>
        ))}
      </div>

      <Label className="mb-2 block">Частота публикаций</Label>
      <div className="flex gap-3 mb-8">
        {FREQUENCIES.map((f) => (
          <button
            key={f.value}
            onClick={() => setFreq(f.value)}
            className={`flex-1 py-2 rounded-lg border text-sm transition-all ${
              freq === f.value ? "border-sky-500 bg-sky-500/10 text-sky-400" : "border-slate-700 text-slate-300 hover:border-slate-500"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Button
        className="w-full"
        disabled={!tone || !freq || loading}
        onClick={() => onNext({ tone_of_voice: tone, posting_frequency: freq })}
      >
        {loading ? "Создаём стратегию..." : "Запустить агента →"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 8: Create `frontend/src/app/(dashboard)/layout.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";

const NAV = [
  { href: "/", label: "📅 Календарь" },
  { href: "/strategy", label: "🎯 Стратегия" },
  { href: "/brand", label: "🏷️ Бренд" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, clearAuth } = useAuthStore();
  const router = useRouter();

  const logout = () => { clearAuth(); router.push("/login"); };

  return (
    <div className="min-h-screen bg-slate-950 flex">
      <aside className="w-48 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <span className="text-sky-400 font-bold text-sm">⚡ SCF</span>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href}
              className={`block px-3 py-2 rounded text-sm ${pathname === item.href ? "bg-slate-800 text-sky-400" : "text-slate-400 hover:text-slate-200"}`}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800">
          <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          <button onClick={logout} className="text-xs text-slate-500 hover:text-red-400 mt-1">Выйти</button>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  );
}
```

- [ ] **Step 9: Create `frontend/src/app/(dashboard)/onboarding/page.tsx`**

```tsx
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";

export default function OnboardingPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-100 mb-2">Добро пожаловать</h1>
      <p className="text-slate-400 mb-8">Настроим вашу контент-фабрику за 2 минуты</p>
      <OnboardingWizard />
    </div>
  );
}
```

- [ ] **Step 10: Verify manually**

```bash
# With backend running:
cd frontend && npm run dev
# Navigate to http://localhost:3000/onboarding
# Complete all 5 steps
# Should redirect to /strategy after completion
```

- [ ] **Step 11: Commit**

```bash
git add frontend/src/
git commit -m "feat: onboarding wizard — 5-step brand setup with workspace creation"
```

---

## Task 9: Strategy View (Frontend)

**Files:**
- Create: `frontend/src/app/(dashboard)/strategy/page.tsx`
- Create: `frontend/src/components/strategy/ContentPillars.tsx`
- Create: `frontend/src/components/strategy/ContentCalendar.tsx`

- [ ] **Step 1: Create `frontend/src/components/strategy/ContentPillars.tsx`**

```tsx
"use client";
import { ContentPillar } from "@/types/api";

const FUNNEL_COLORS: Record<string, string> = {
  tofu: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  mofu: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  bofu: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  retention: "bg-green-500/20 text-green-400 border-green-500/30",
};

export function ContentPillars({ pillars }: { pillars: ContentPillar[] }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-100 mb-4">Контент-столбы</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {pillars.map((p) => (
          <div key={p.id} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-slate-100 mb-1">{p.title}</h3>
            <p className="text-xs text-slate-400 mb-3">{p.description}</p>
            <div className="flex flex-wrap gap-1">
              {p.funnel_stages.split(",").map((stage) => (
                <span key={stage} className={`text-xs px-2 py-0.5 rounded border ${FUNNEL_COLORS[stage.trim()] ?? ""}`}>
                  {stage.trim().toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/strategy/ContentCalendar.tsx`**

```tsx
"use client";
import { ContentPlanItem } from "@/types/api";

const NETWORK_COLORS: Record<string, string> = {
  instagram: "text-pink-400",
  vk: "text-blue-400",
  telegram: "text-purple-400",
};

const FUNNEL_DOT: Record<string, string> = {
  tofu: "bg-blue-500",
  mofu: "bg-purple-500",
  bofu: "bg-amber-500",
  retention: "bg-green-500",
};

export function ContentCalendar({ items }: { items: ContentPlanItem[] }) {
  const byDate = items.reduce<Record<string, ContentPlanItem[]>>((acc, item) => {
    (acc[item.planned_date] ??= []).push(item);
    return acc;
  }, {});

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-100 mb-4">Контент-план на 4 недели</h2>
      <div className="space-y-3">
        {Object.entries(byDate).sort(([a], [b]) => a.localeCompare(b)).map(([date, dayItems]) => (
          <div key={date} className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            <div className="bg-slate-800 px-4 py-2 text-xs font-medium text-slate-400">
              {new Date(date).toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
            </div>
            <div className="divide-y divide-slate-800">
              {dayItems.map((item) => (
                <div key={item.id} className="px-4 py-3 flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${FUNNEL_DOT[item.funnel_stage]}`} />
                  <span className={`text-xs font-medium w-20 flex-shrink-0 ${NETWORK_COLORS[item.network] ?? ""}`}>
                    {item.network} · {item.format}
                  </span>
                  <span className="text-sm text-slate-200 flex-1">{item.topic}</span>
                  <span className="text-xs text-slate-500 uppercase">{item.funnel_stage}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/app/(dashboard)/strategy/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { ContentPillars } from "@/components/strategy/ContentPillars";
import { ContentCalendar } from "@/components/strategy/ContentCalendar";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { ContentPillar, ContentPlanItem } from "@/types/api";

export default function StrategyPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [pillars, setPillars] = useState<ContentPillar[]>([]);
  const [plan, setPlan] = useState<ContentPlanItem[]>([]);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ws) return;
    Promise.all([
      api.get(`/strategy/workspaces/${ws.id}/pillars`),
      api.get(`/strategy/workspaces/${ws.id}/plan`),
    ]).then(([p, pl]) => {
      setPillars(p.data);
      setPlan(pl.data);
    }).finally(() => setLoading(false));
  }, [ws]);

  const regenerate = async () => {
    if (!ws) return;
    setGenerating(true);
    try {
      const res = await api.post(`/strategy/workspaces/${ws.id}/generate`);
      setPillars(res.data.pillars);
      setPlan(res.data.plan_items);
    } finally {
      setGenerating(false);
    }
  };

  if (!ws) return <p className="text-slate-400">Сначала создайте воркспейс</p>;
  if (loading) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Стратегия</h1>
        <Button onClick={regenerate} disabled={generating} variant="outline">
          {generating ? "Генерируем..." : "Перегенерировать"}
        </Button>
      </div>

      {pillars.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-slate-400 mb-4">Стратегия ещё не создана</p>
          <Button onClick={regenerate} disabled={generating}>
            {generating ? "Агент думает..." : "Создать стратегию"}
          </Button>
        </div>
      ) : (
        <div className="space-y-8">
          <ContentPillars pillars={pillars} />
          <ContentCalendar items={plan} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify manually**

```bash
# With backend + frontend running
# After onboarding, should redirect to /strategy
# Click "Создать стратегию" — should call Claude API and show pillars + calendar
# Verify funnel balance in the calendar
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(dashboard\)/strategy/ frontend/src/components/strategy/
git commit -m "feat: strategy view — content pillars and 4-week content calendar"
```

---

## Task 10: Dashboard Home + Brand Page

**Files:**
- Create: `frontend/src/app/(dashboard)/page.tsx`
- Create: `frontend/src/app/(dashboard)/brand/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/(dashboard)/page.tsx`**

```tsx
"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useWorkspaceStore } from "@/store/workspace";
import { useAuthStore } from "@/store/auth";

export default function DashboardPage() {
  const router = useRouter();
  const ws = useWorkspaceStore((s) => s.current);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!user) { router.push("/login"); return; }
    if (!ws) { router.push("/onboarding"); return; }
    router.push("/strategy");
  }, [user, ws, router]);

  return null;
}
```

- [ ] **Step 2: Create `frontend/src/app/(dashboard)/brand/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { Brand } from "@/types/api";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function BrandPage() {
  const ws = useWorkspaceStore((s) => s.current);
  const [brand, setBrand] = useState<Brand | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Brand>>({});

  useEffect(() => {
    if (!ws) return;
    api.get(`/workspaces/${ws.id}/brand`).then((r) => {
      setBrand(r.data);
      setForm(r.data);
    });
  }, [ws]);

  const save = async () => {
    if (!ws) return;
    const res = await api.patch(`/workspaces/${ws.id}/brand`, {
      description: form.description,
      target_audience: form.target_audience,
      tone_of_voice: form.tone_of_voice,
    });
    setBrand(res.data);
    setEditing(false);
  };

  if (!brand) return <p className="text-slate-400">Загрузка...</p>;

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-100">{brand.name}</h1>
        <Button onClick={() => setEditing(!editing)} variant="outline" size="sm">
          {editing ? "Отмена" : "Редактировать"}
        </Button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
        <div>
          <Label>Описание</Label>
          {editing
            ? <textarea className="mt-1 w-full bg-slate-800 border border-slate-700 rounded p-3 text-sm text-slate-100 resize-none" rows={3}
                value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            : <p className="text-sm text-slate-300 mt-1">{brand.description}</p>}
        </div>
        <div>
          <Label>Целевая аудитория</Label>
          {editing
            ? <textarea className="mt-1 w-full bg-slate-800 border border-slate-700 rounded p-3 text-sm text-slate-100 resize-none" rows={2}
                value={form.target_audience ?? ""} onChange={(e) => setForm({ ...form, target_audience: e.target.value })} />
            : <p className="text-sm text-slate-300 mt-1">{brand.target_audience}</p>}
        </div>
        <div>
          <Label>Соцсети</Label>
          <div className="flex gap-2 mt-1">
            {brand.social_accounts.map((a) => (
              <span key={a.id} className="text-xs px-3 py-1 bg-slate-800 border border-slate-700 rounded-full text-slate-300">
                {a.network}
              </span>
            ))}
          </div>
        </div>
        {editing && <Button onClick={save} className="w-full">Сохранить</Button>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Run full backend test suite**

```bash
cd backend
pytest tests/ -v
# Expected: all tests PASSED
```

- [ ] **Step 4: Verify full flow manually**

```
1. Register at /register
2. Login at /login
3. Redirected to /onboarding
4. Complete 5 steps
5. Redirected to /strategy
6. Click "Создать стратегию" → pillars and calendar appear
7. Navigate to /brand → see brand profile
8. Edit description and save
```

- [ ] **Step 5: Final commit**

```bash
git add frontend/src/app/\(dashboard\)/
git commit -m "feat: dashboard home, brand profile page — Phase 1 complete"
```

---

## Phase 1 Complete

At this point the following is working and tested:
- User registration and login with JWT
- Workspace creation and role-based access (Owner / Editor / Approver)
- Brand profile setup with social account selection
- Autonomous strategy generation via Claude API (content pillars + 4-week content plan with funnel stages)
- Full onboarding wizard (5 steps)
- Strategy view with pillars and calendar
- Brand profile view and edit

**Next:** Phase 2 — Content Core (Asset Library, Repurposing Engine, Research Path, Draft Generator, Approval Workflow)
