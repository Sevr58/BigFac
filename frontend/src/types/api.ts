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
