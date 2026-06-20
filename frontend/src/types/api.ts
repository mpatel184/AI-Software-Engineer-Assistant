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
