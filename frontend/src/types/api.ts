/**
 * API contracts.
 *
 * Mirrors the DRF serializers. Keeping these hand-written and narrow (rather
 * than generating a sprawling client) means the frontend states exactly what it
 * relies on, and a backend field that quietly disappears becomes a type error.
 */

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  meta?: PageMeta;
  error?: ApiError;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface PageMeta {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  next: string | null;
  previous: string | null;
}

export interface Paginated<T> {
  results: T[];
  meta: PageMeta | null;
}

export type ProblemStatus =
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'DEPARTMENT_ASSIGNED'
  | 'ACKNOWLEDGED'
  | 'INSPECTION'
  | 'ACTION_PLANNED'
  | 'WORK_STARTED'
  | 'WORK_IN_PROGRESS'
  | 'COMPLETED'
  | 'VERIFICATION'
  | 'RESOLVED'
  | 'REJECTED'
  | 'DUPLICATE'
  | 'INSUFFICIENT_EVIDENCE'
  | 'OUTSIDE_JURISDICTION'
  | 'ALREADY_RESOLVED';

export type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type VerificationState = 'UPLOADED' | 'UNDER_VERIFICATION' | 'VERIFIED' | 'REJECTED';

export interface PublicUser {
  id: string;
  display_name: string;
  avatar_url: string;
  role: string;
  is_professionally_verified: boolean;
  verified_category: string;
  verification_badge: string | null;
  state: string;
  professional_profile: ProfessionalProfile | null;
}

export interface ProfessionalProfile {
  category: string;
  category_display: string;
  domain: string;
  domain_display: string;
  headline: string;
  bio: string;
  years_of_experience: number;
  expertise_areas: string[];
  designation?: string;
  organization?: string;
  state?: string;
  city?: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  display_name: string;
  avatar_url: string;
  role: string;
  is_professionally_verified: boolean;
  verified_category: string;
  state: string;
  city: string;
  onboarding_completed: boolean;
  is_banned: boolean;
  professional_profile: ProfessionalProfile | null;
}

export interface MediaItem {
  id: string;
  media_type: 'IMAGE' | 'VIDEO' | 'DOCUMENT' | 'AUDIO';
  purpose: 'GENERAL' | 'BEFORE' | 'DURING' | 'AFTER' | 'EVIDENCE' | 'DOCUMENT';
  url: string;
  thumbnail_url: string;
  caption: string;
  /** Uploaded is not verified -- the UI must show the difference (spec 17). */
  verification_status: VerificationState;
  verified_at: string | null;
  created_at: string;
}

export interface ProblemLocation {
  city: string;
  district: string;
  state: string;
  latitude: number | null;
  longitude: number | null;
  display: string;
}

export interface ProblemCard {
  id: string;
  title: string;
  slug: string;
  status: ProblemStatus;
  status_display: string;
  priority: Priority;
  priority_display: string;
  category: { id: string; name: string; path: string } | null;
  department: { id: string; name: string } | null;
  location: ProblemLocation;
  support_count: number;
  report_count: number;
  comment_count: number;
  evidence_count: number;
  cover_image: { url: string; verified: boolean } | null;
  reporter: { display_name: string; is_anonymous: boolean } & Partial<PublicUser>;
  viewer_has_supported: boolean;
  cluster_id: string | null;
  created_at: string;
  last_activity_at: string;
  last_status_change_at: string | null;
  resolved_at: string | null;
}

export interface TimelineEvent {
  id: string;
  kind: string;
  kind_display: string;
  title: string;
  description: string;
  from_status: string;
  to_status: string;
  actor_label: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface GovernmentResponse {
  id: string;
  kind: string;
  kind_display: string;
  message: string;
  department_name: string;
  expected_resolution_date: string | null;
  reference_number: string;
  media: MediaItem[];
  created_at: string;
}

export interface ProblemDetail extends ProblemCard {
  description: string;
  media: MediaItem[];
  timeline: TimelineEvent[];
  government_responses: GovernmentResponse[];
  allowed_transitions: ProblemStatus[];
  cluster: {
    id: string;
    title: string;
    problem_count: number;
    total_support: number;
  } | null;
  days_open: number;
  closure_reason: string;
  view_count: number;
}

export type ExperienceType =
  | 'PROFESSIONAL_EXPERIENCE'
  | 'ROOT_CAUSE_ANALYSIS'
  | 'POLICY_IDEA'
  | 'RECOMMENDATION'
  | 'BEST_PRACTICE'
  | 'GOVERNANCE_IMPROVEMENT'
  | 'COST_REDUCTION'
  | 'PROCESS_IMPROVEMENT'
  | 'TECHNOLOGY_IMPROVEMENT'
  | 'OTHER';

export interface ExperienceCard {
  id: string;
  title: string;
  slug: string;
  experience_type: ExperienceType;
  type_display: string;
  summary: string;
  author: PublicUser | null;
  category: { id: string; name: string } | null;
  state: string;
  city: string;
  support_count: number;
  comment_count: number;
  evidence_count: number;
  credibility_score: number;
  related_problem_count: number;
  viewer_has_supported: boolean;
  created_at: string;
  last_activity_at: string;
}

export interface ExperienceDetail extends ExperienceCard {
  observed_problem: string;
  context: string;
  root_cause: string;
  personal_experience: string;
  recommendation: string;
  implementation: string;
  expected_impact: string;
  challenges: string;
  cost_implications: string;
  media: MediaItem[];
  related_problems: Array<{
    id: string;
    title: string;
    status: ProblemStatus;
    support_count: number;
    relevance_note: string;
  }>;
  author_was_verified: boolean;
  view_count: number;
}

export interface Comment {
  id: string;
  body: string;
  author: PublicUser | null;
  depth: number;
  reply_count: number;
  replies: Comment[];
  edited_at: string | null;
  created_at: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  path: string;
  depth: number;
  icon: string;
  description: string;
  children: Category[];
}

export interface Department {
  id: string;
  name: string;
  slug: string;
  path: string;
  level: string;
  state: string;
  district: string;
  city: string;
  avg_resolution_days: number | null;
  resolved_count: number;
}

export interface PublicStats {
  problems_reported: number;
  active_problems: number;
  problems_resolved: number;
  citizens_supporting: number;
  experiences_shared: number;
  government_responses: number;
  projects_completed: number;
  average_resolution_days: number | null;
  computed_at: string;
}

export interface RankingTab {
  key: string;
  label: string;
  description: string;
}

export interface IssueCluster {
  id: string;
  title: string;
  description: string;
  status: string;
  category_name: string;
  department_name: string;
  city: string;
  district: string;
  state: string;
  problem_count: number;
  total_support_count: number;
  unique_reporter_count: number;
  aggregate_label: string;
  review_required: boolean;
  created_at: string;
}

export interface SessionPayload {
  access_token: string;
  expires_in: number;
  refresh_token: string;
  token_type: string;
  is_new_user: boolean;
  requires_onboarding: boolean;
  user: CurrentUser;
  next?: string;
}

export interface Notification {
  id: string;
  kind: string;
  title: string;
  body: string;
  link_path: string;
  metadata: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}
