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
