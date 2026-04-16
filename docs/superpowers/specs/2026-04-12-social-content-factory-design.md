# Social Content Factory — Design Spec

**Date:** 2026-04-12
**Status:** Approved
**Author:** Claude Code + User

---

## 1. Product Summary

A multi-tenant SaaS platform that replaces up to 90% of routine SMM work through an autonomous AI agent. The agent builds strategy, creates content plans, researches competitors and trends, generates content for multiple social networks, and publishes approved posts. Humans retain only final approval, live recording, and brand judgment.

Target: agencies, in-house marketing teams, small and medium businesses. Russian market focus. MVP networks: Instagram, VK, Telegram.

---

## 2. Architecture

### Approach: Service-oriented (2 services)

**API Service (FastAPI + Next.js)**
- Handles all HTTP requests and WebSocket connections from the web dashboard
- Manages auth, workspaces, brand profiles, content CRUD, approval workflow, scheduling
- Next.js frontend served separately or via same container

**Worker Service (Celery)**
- Handles all background and heavy tasks: transcription, scene detection, clip extraction, AI generation, publishing, analytics sync
- Celery Beat handles scheduled publishing and recurring jobs
- Isolated from API — video processing does not impact API response times

**Shared infrastructure**
- PostgreSQL (Yandex Managed) — primary database
- Redis — Celery broker and cache
- Yandex Object Storage (S3-compatible) — video, audio, image storage
- Nginx — reverse proxy

**Deployment**
- Docker Compose on a single Yandex Cloud server (4 CPU / 8 GB RAM) for MVP
- Scale horizontally by adding Worker instances when needed

---

## 3. Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (React, SSR) |
| Backend API | Python FastAPI |
| Database | PostgreSQL — Yandex Managed |
| Background jobs | Redis + Celery + Celery Beat |
| File storage | Yandex Object Storage (S3) |
| Transcription | OpenAI Whisper API |
| Scene detection | PySceneDetect |
| Video processing | FFmpeg |
| AI text + strategy | Claude API (Sonnet for complex tasks, Haiku for fast/cheap tasks) |
| Image generation | Stability AI API (SDXL / SD3) |
| Web research | Tavily API |
| Hosting | Yandex Cloud |
| Notifications | Telegram Bot API (secondary layer only) |
| Billing | None in MVP — workspaces created manually by admin |

---

## 4. User Roles

Three roles per workspace:

| Role | Capabilities |
|---|---|
| **Owner** | Full access: settings, strategy, brand, team management, billing (future), final approval |
| **Editor** | Create content, upload assets, submit drafts for approval, view analytics |
| **Approver** | Review drafts, approve or reject with comments, cannot create or edit |

Approval workflow: Editor submits → Approver approves → Owner has override on all stages.

---

## 5. Content Agent — Core Concept

The autonomous agent is the heart of the system. It does not wait for human instructions to produce content — it runs on a schedule driven by the content plan it created itself.

### Agent decision flow

```
Trigger (plan / user command / trend / brand rule)
    ↓
Agent checks: what is needed? what funnel stage?
    ↓
Agent checks: is there a source asset in the library?
    ├─ YES → Repurposing Path
    └─ NO  → Research Path
    ↓
Agent generates content per network and format
    ↓
Human approves or rejects
    ↓
System publishes
    ↓
Agent learns from results → updates future decisions
```

### Triggers

- **Content plan** (primary): agent executes tasks it scheduled itself
- **User command**: direct instruction ("make a post about X")
- **Trend detected**: agent found a relevant topic during research
- **Brand rules**: recurring tasks defined during onboarding

### Repurposing Path

1. Upload source asset (video, audio, podcast, screen recording, interview)
2. Whisper API → transcription
3. PySceneDetect + FFmpeg → scene detection and clip extraction
4. Claude API → extract hooks, key points, quotes, CTAs, story segments (content atoms)
5. Claude API → generate drafts per network and format
6. Human task generated if live footage is still needed

### Research Path (no source asset)

1. Tavily/Serper → web search for fresh relevant topics
2. Competitor analysis → monitor public posts and engagement via social network APIs and public feeds to identify what content works in the niche
3. Claude API → topic selection, angle, structure
4. Claude API → write text content
5. Image generation → visuals via Stability AI API
6. Assemble drafts per network and format

---

## 6. Content Funnel Integration

Every piece of content in the plan is tagged with a funnel stage. The agent uses this tag when generating copy and CTAs. Analytics tracks conversion by funnel stage.

| Stage | Purpose | CTA style | Content examples |
|---|---|---|---|
| **TOFU** | Awareness, reach | Subscribe, save | Trends, facts, entertainment, educational Reels |
| **MOFU** | Consideration | Learn more, link | Cases, comparisons, carousels, polls |
| **BOFU** | Conversion | Buy, book, message | Reviews, offers, objection handling, demos |
| **Retention** | Loyalty | Share, recommend | Tips, behind-the-scenes, community, UGC |

The agent maintains a healthy balance across stages in the content plan. It does not allow an excess of BOFU posts that would feel pushy.

UTM parameters are applied to all links per post, tagged with network, format, funnel stage, and campaign. Yandex Metrica tracks downstream actions and lead attribution.

---

## 7. Social Network Formats

### Instagram
- Reels (vertical video)
- Carousel (multi-slide)
- Static post (image + caption)
- Stories with poll

### VKontakte
- Clip (short vertical video)
- Long post with photo
- Poll post
- Long video

### Telegram
- Longread post in channel
- Voice message
- Image post
- Poll
- Link announcement

---

## 8. Content Strategy Engine

On onboarding (and periodically thereafter), the agent:

1. Reads brand profile: company type, description, goals, target audience, tone of voice, available assets
2. Selects active social networks
3. Generates content pillars (3–6 strategic themes for the brand)
4. Generates content calendar (posts per network per week, formats, funnel stages)
5. Assigns formats and frequencies per network based on platform best practices

The Owner reviews and approves the generated strategy. From that point the agent runs autonomously on the agreed plan.

---

## 9. Core Data Entities

- **Workspace** — top-level container for a team/brand
- **User** — belongs to a workspace with a role (Owner / Editor / Approver)
- **Brand** — brand profile, tone, goals, target audience
- **SocialAccount** — connected account per network (Instagram page, VK community, Telegram channel)
- **ContentPillar** — strategic content theme
- **Campaign** — optional grouping of content items
- **ContentPlan** — calendar of planned content items with funnel stage, format, network, date
- **SourceAsset** — uploaded raw file (video, audio, text)
- **ContentAtom** — extracted element from a source asset (hook, quote, CTA, key point, clip)
- **Draft** — generated content item for a specific network and format, with status
- **HumanTask** — task for a team member (record video, take photo, provide voice)
- **ApprovalRequest** — review request linked to a draft
- **ScheduledPost** — approved draft queued for publishing
- **PublishedPost** — post record after publishing, with network post ID
- **PostMetrics** — performance data pulled from network APIs
- **LeadEvent** — lead or conversion attributed to a post via UTM + Yandex Metrica

---

## 10. Draft Status Lifecycle

```
Draft → Needs Review → Approved → Scheduled → Publishing → Published
                    ↘                                    ↘ Failed → Retrying → Published
                     Rejected → (revised) → Needs Review          ↘ Archived (after max retries)
```

---

## 11. Publishing Engine

- Per-network adapters: Instagram (Meta Graph API), VK (VK API), Telegram (Bot API)
- Celery Beat triggers publishing jobs at scheduled time
- Retry logic with exponential backoff on failure
- Publishing log per post: status, timestamp, error message if any
- Post status visible in dashboard in real time

---

## 12. Analytics

Dashboard shows:

- Reach, views, engagement, saves, clicks, CTR per post
- Performance by network, format, content pillar, funnel stage, campaign
- Lead attribution: which posts generated leads (via UTM + Yandex Metrica)
- Top and bottom performing content summaries
- Source asset ROI: which uploaded video generated the most useful derivatives

Agent uses analytics results to adjust the content plan and generation decisions going forward.

---

## 13. UX — Primary Screens

1. **Dashboard** — metrics overview, upcoming posts, pending approvals, team tasks, top content
2. **Content Calendar** — weekly/monthly view of planned and published content
3. **Asset Library** — uploaded source files, tagging, search, reuse
4. **Drafts & Approval** — queue for Editor review and Approver sign-off
5. **Publishing Queue** — approved posts pending publication, with status
6. **Analytics** — performance dashboard with funnel breakdown and lead attribution
7. **Strategy** — content pillars, funnel balance, content plan overview
8. **Human Tasks** — recording and photo tasks for team members
9. **Brand Settings** — brand profile, tone, networks, onboarding data
10. **Team Settings** — user management, role assignment

**Telegram bot** — secondary layer only: approval alerts, publish confirmations, error notifications, quick summary reports.

---

## 14. Implementation Phases

### Phase 1 — Foundation
- Auth + JWT + user management
- Workspace creation and role system
- Onboarding wizard (brand profile, network selection, goals, tone)
- Brand profile storage
- Strategy engine: content pillars + content plan generation via Claude API

### Phase 2 — Content Core
- Asset Library: upload, storage (S3), tagging, search
- Repurposing engine: Whisper transcription, PySceneDetect, FFmpeg clip extraction, content atom extraction
- Research path: web search via Tavily/Serper, competitor analysis
- Draft generator: Claude API for all formats per network
- Approval workflow: review queue, approve/reject/comment, version history
- Human task system: task creation, upload, handoff back to agent

### Phase 3 — Distribution & Analytics
- Publishing engine: Instagram, VK, Telegram adapters
- Scheduling, retry logic, publishing logs
- Analytics dashboard: post metrics, network/format/funnel breakdown
- Lead attribution: UTM generation, Yandex Metrica integration
- Agent feedback loop: analytics → strategy adjustment

---

## 15. Non-Functional Requirements

- All heavy jobs (video, AI) run in the Worker service, never blocking the API
- Large file uploads go directly to S3 via presigned URLs — no routing through API
- All publishing actions require prior approval — no automated publishing without human sign-off
- Audit log for approvals and publishing actions
- Version history on drafts
- Modular adapter pattern for social networks — adding a new network requires a new adapter only, no core changes
- System must handle Russian-language content natively (Whisper, Claude both handle Russian well)

---

## 16. Out of Scope for MVP

- Billing and subscription management
- White-label support
- Hyper-realistic AI video generation
- YouTube, Pinterest, or other networks beyond Instagram, VK, Telegram
- Advanced CRM replacement
- Native mobile app
