/**
 * Shared API types mirroring backend Pydantic schemas. Kept in sync as each
 * module is implemented. Pagination/list envelope is defined up front since
 * every list endpoint uses it.
 */

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type JobStatus = "queued" | "running" | "completed" | "failed";
export type RepoStatus = "pending" | "cloning" | "indexing" | "ready" | "failed";
export type Severity = "info" | "low" | "medium" | "high" | "critical";

export type UserRole = "admin" | "member";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export type RepoSource = "github" | "upload";

export interface Repository {
  id: string;
  name: string;
  source: RepoSource;
  status: RepoStatus;
  github_url: string | null;
  default_branch: string | null;
  primary_language: string | null;
  languages: Record<string, number>;
  file_count: number;
  total_lines: number;
  size_bytes: number;
  commit_sha: string | null;
  error_message: string | null;
  indexed_at: string | null;
  created_at: string | null;
}

export interface CreateRepoPayload {
  github_url: string;
  name?: string;
}

export type AnalysisType =
  | "architecture"
  | "dependencies"
  | "complexity"
  | "duplication"
  | "dead_code"
  | "bugs"
  | "security";

export interface AnalysisSummary {
  project_summary?: string;
  architecture_overview?: string;
  tech_stack?: string[];
  folder_explanation?: { path: string; purpose: string }[];
}

export interface AnalysisMetrics {
  file_count?: number;
  total_lines?: number;
  languages?: Record<string, number>;
  avg_complexity?: number;
  max_complexity?: number;
  complexity_hotspots?: { file_path: string; lines: number; estimated_complexity: number }[];
  dependencies?: Record<string, string[]>;
  doc_coverage_pct?: number;
  folder_summary?: { path: string; files: number; lines: number }[];
}

export interface Analysis {
  id: string;
  repository_id: string;
  type: AnalysisType;
  status: JobStatus;
  summary: AnalysisSummary;
  metrics: AnalysisMetrics;
  score: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
}
