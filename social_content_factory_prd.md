# Social Content Factory for Claude Code

## Purpose

Build a multi-tenant SaaS product that helps companies replace up to 90% of the operational work of an SMM specialist through strategy generation, content planning, human-content coordination, content repurposing, publishing, and analytics.

This project should be designed so that each customer can choose which social networks to enable during onboarding. The MVP must focus on Instagram, VK, and Telegram, with a modular architecture that allows future expansion to other social networks.

The product is not a white-label system for reselling. It is an internal productivity tool for agencies, teams, and companies.

---

## Product Vision

The system should function as a social content factory:

- It collects business input, brand information, offers, target audience details, and existing assets.
- It generates social media strategy, content pillars, content calendars, and post ideas.
- It prepares tasks for human creators when live video, photos, voice, or expertise are needed.
- It repurposes one source asset into many publishable formats.
- It publishes approved content to selected social networks.
- It tracks performance, leads, and channel-level effectiveness.
- It learns from the results and improves future planning.

The primary goal is not to fully replace humans, but to automate repetitive work, coordination, and first-draft production while leaving only the highest-value human decisions, approvals, and live content creation.

---

## Core Principles

1. Modular first. Every network, content type, and workflow must be optional.
2. Human approval is mandatory before publishing.
3. Web dashboard is the primary interface.
4. Telegram bot is optional and only for monitoring, reminders, and quick status updates.
5. One customer may manage one or more brands, but the MVP can assume one brand per customer profile.
6. The system must support content repurposing from one source asset into multiple outputs.
7. The system must support a unified analytics base with simple dashboards and deeper drill-down.
8. The architecture must be reliable, inexpensive to run, and easy to extend.

---

## MVP Scope

### Included in MVP

- User onboarding and workspace setup.
- Social network selection during onboarding.
- Brand profile setup.
- Content strategy generation.
- Content calendar generation.
- Content idea generation.
- Human-content task preparation.
- Asset upload and content repository.
- Content repurposing from long-form video into short clips, posts, stories, and website snippets.
- Draft generation for captions, scripts, carousels, stories, and posting text.
- Approval workflow.
- Publishing workflow for Instagram, VK, and Telegram.
- Analytics dashboard.
- Lead attribution via UTM and Yandex Metrica.
- Performance summaries by network, format, campaign, and post.

### Excluded from MVP

- Full white-label support.
- Direct monetization tooling for reselling.
- Hyper-realistic AI video generation as a core feature.
- Full support for every Russian social network on day one.
- Advanced CRM replacement.
- Complex media studio tools that are not needed for the core workflow.

---

## Target Users

The product should work for a broad range of companies, but the system must be designed around practical use cases:

- Small and medium businesses.
- In-house marketing teams.
- Agencies using the tool internally to replace junior SMM workload.
- Businesses that produce content in-house and need automation around planning and publishing.

The onboarding flow must not assume a single segment. Instead, the user selects the business type, goals, available assets, social networks, and preferred workflow.

---

## Platform Strategy

### Instagram

Instagram must support:

- Reels planning and repurposing.
- Story sequences.
- Static posts.
- Carousels.
- Caption generation.
- Human-content workflows.

The system should not rely on building a fragile direct posting system inside the core product if a third-party publishing provider is required.

### VK

VK must support:

- Community posts.
- Clips.
- Long and short video formats.
- Visual posts.
- Content distribution into a community wall.
- Metrics by post and format.

VK is a priority because it is a core Russian social network and offers a strong opportunity for automation.

### Telegram

Telegram must support:

- Channel publishing.
- Post drafts.
- Content previews.
- Voice note or audio support where useful.
- Simple monitoring and notifications through a bot.
- Analytics connected to posts, clicks, and leads.

Telegram should be treated as a distribution and trust-building channel, not as a heavy visual design channel.

---

## Content Model

The system should be built around reusable content objects, not around isolated posts.

### Core entities

- Brand.
- Workspace.
- Social network.
- Content pillar.
- Campaign.
- Content idea.
- Source asset.
- Content atom.
- Draft.
- Approval request.
- Scheduled post.
- Published post.
- Performance report.
- Lead event.

### Content atom concept

A single source asset should be broken into reusable atoms:

- Hook.
- Key point.
- Quote.
- CTA.
- Story segment.
- Visual cue.
- B-roll suggestion.
- Caption fragment.
- Carousel slide text.
- Story frame text.

These atoms should be recombined into multiple deliverables for multiple networks.

---

## Source Asset Workflow

The product must support the following workflow:

1. A person or team uploads a large source asset, such as a long video, interview, website recording, product demo, podcast extract, or live recording.
2. The system transcribes, summarizes, and analyzes the asset.
3. The system extracts content atoms and possible angles.
4. The system generates outputs for different channels.
5. The system creates human tasks if a live recording, additional footage, voice, or approval is needed.
6. The person uploads the missing live material or approves the draft.
7. The system schedules or posts the content.
8. The system measures the outcome and stores results for future optimization.

This workflow must be a first-class product feature.

---

## Human Content Workflow

Human content is a required part of the system.

The product must be able to prepare:

- Topic.
- Script.
- Talking points.
- On-camera instructions.
- Deadlines.
- Content destination.
- Required format.
- Required aspect ratio.
- Suggested hook.
- Suggested CTA.

The user should be able to open a task, read the text, record the video, and upload it to the correct folder or workflow stage.

The system must then transform that live material into multiple derivative assets.

---

## Repurposing Requirements

One source video should be transformed into as many useful outputs as possible.

Examples:

- One long video for a website or landing page.
- Multiple short vertical clips for Instagram and VK.
- Multiple short clips for YouTube Shorts.
- Several story frames.
- Static images or placeholder visuals.
- Quote cards.
- Carousel content.
- Summary posts.
- Telegram channel posts.
- Hook variations for A/B testing.

The repurposing engine should not simply cut clips. It should understand structure, message, emotional emphasis, and distribution goals.

---

## AI Video Policy

AI video generation is not a core MVP feature.

The system may support limited AI-generated video elements for non-hyper-realistic use cases such as:

- Abstract motion backgrounds.
- Schematics.
- Placeholder visuals.
- Simple animated transitions.
- Informational motion graphics.

However, the product should assume that high-value video content comes from real human footage. The system must support live content ingestion and repurposing at the center of the workflow.

---

## Publishing Requirements

The platform must support a publishing pipeline with the following states:

- Draft.
- Needs review.
- Approved.
- Scheduled.
- Published.
- Failed.
- Retrying.
- Archived.

Publishing must only happen after approval.

The system must support:

- Scheduling.
- Queue management.
- Retry logic.
- Per-network publishing rules.
- Post status tracking.
- Publishing logs.
- Error reporting.

---

## Analytics Requirements

Analytics must be one of the strongest parts of the system.

The product must track:

- Reach.
- Views.
- Engagement.
- Saves.
- Clicks.
- CTR.
- Leads.
- Conversions.
- Channel performance.
- Format performance.
- Content pillar performance.
- Campaign performance.
- Creator performance if relevant.

### Analytics goals

The dashboard should let a user quickly understand:

- What content worked.
- What content failed.
- Which network performed best.
- Which format performed best.
- Which posts generated leads.
- Which content pillar is strongest.
- Which source asset generated the most useful derivatives.

### Lead attribution

The system must integrate Yandex Metrica and use UTM parameters to connect social content to website actions and leads.

---

## UX Requirements

### Primary interface

The main interface must be a web dashboard.

The dashboard should include:

- Onboarding wizard.
- Brand settings.
- Network selection.
- Content calendar.
- Asset library.
- Draft editor.
- Approval queue.
- Publishing queue.
- Analytics view.
- Performance summary.

### Telegram bot

A Telegram bot may exist only as a secondary layer for:

- Status notifications.
- Approval alerts.
- Publish alerts.
- Error alerts.
- Quick summary reports.

The Telegram bot should not be the main operational interface.

---

## System Behavior

The system should behave like a content operating system.

It should not merely generate isolated posts. It should:

- Understand the brand.
- Build a strategy.
- Transform strategy into a plan.
- Produce content.
- Map tasks to humans.
- Repurpose source assets.
- Publish content.
- Measure results.
- Learn from outcomes.

The system should help replace most of the repetitive work of an SMM specialist while preserving the human roles that require judgment, authenticity, and final approval.

---

## Suggested Technical Direction

Use the simplest reliable stack that supports future scale.

### Recommended architecture

- Frontend: Next.js.
- Backend: Python FastAPI.
- Database: PostgreSQL.
- Background jobs: Redis + Celery or RQ.
- File storage: S3-compatible object storage.
- Workflow automation: n8n.
- Analytics dashboard: custom UI plus optional BI layer.
- AI orchestration: Claude Code for development and agent-assisted workflows.

The final implementation must remain modular, testable, and maintainable.

---

## Required Product Modules

### 1. Authentication and workspaces

- Login.
- Workspace creation.
- User roles.
- Brand ownership.
- Multi-account support.

### 2. Onboarding

- Company type.
- Brand description.
- Goals.
- Target audience.
- Selected social networks.
- Content frequency.
- Tone of voice.
- Asset availability.

### 3. Strategy engine

- Content pillars.
- Goals.
- Formats.
- Platform rules.
- Posting frequency.
- Funnel logic.

### 4. Content planning

- Calendar generation.
- Topic suggestions.
- Format mapping.
- Campaign planning.
- Human task assignment.

### 5. Asset library

- Upload large video files.
- Organize source assets.
- Tag assets.
- Search assets.
- Reuse assets across campaigns.

### 6. Repurposing engine

- Transcription.
- Summarization.
- Scene detection.
- Clip extraction.
- Text extraction.
- Format conversion.

### 7. Draft generator

- Captions.
- Scripts.
- Carousel slide copy.
- Story copy.
- Telegram posts.
- VK posts.
- CTA variants.

### 8. Approval workflow

- Review queue.
- Comments.
- Approve / reject.
- Revision requests.
- Version history.

### 9. Publishing engine

- Network adapters.
- Scheduling.
- Post states.
- Logs.
- Error handling.

### 10. Analytics and reporting

- Performance dashboard.
- Content insights.
- Lead attribution.
- Exportable reports.
- Best/worst content summaries.

---

## Non-Functional Requirements

- The system must be reliable.
- The system must be maintainable.
- The system must be inexpensive to operate.
- The system must be modular.
- The system must be easy to expand.
- The system must support future networks without rewriting the core.
- The system must not depend on fragile hacks as the main architecture.
- The system must handle large media uploads safely.
- The system must support auditability and version history.

---

## Success Criteria

The product is successful if a company can:

1. Connect a brand.
2. Select the social networks they want.
3. Enter basic brand data.
4. Receive a useful strategy.
5. Upload one large content asset.
6. Turn that asset into many outputs.
7. Assign missing human tasks.
8. Approve content.
9. Publish content.
10. See clear analytics and lead attribution.
11. Repeat the process weekly without heavy manual coordination.

---

## Claude Code Execution Instructions

When implementing this project in Claude Code, follow the project start workflow:

1. Research the market and risks.
2. Brainstorm the product clearly.
3. Write a PLAN file.
4. Run pre-mortem on the plan.
5. Break work into tasks.
6. Implement with TDD.
7. Review code after each major block.

The implementation must follow the project start guide and must not skip validation, planning, or pre-mortem.

---

## Final Product Definition

This product is a modular SaaS content factory for Russian-market social media operations.

Its purpose is to reduce the workload of SMM teams by automating:

- Strategy generation.
- Planning.
- Content drafting.
- Human task preparation.
- Repurposing.
- Posting.
- Analytics.

The system should leave humans responsible for:

- Live recording.
- Brand judgment.
- Final approval.
- Crisis response.
- Exceptional decisions.

That is the product that should be built.
