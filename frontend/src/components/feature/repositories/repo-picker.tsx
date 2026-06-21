"use client";

import { EmptyState } from "@/components/empty-states/empty-state";
import { RepoStatusBadge } from "@/components/feature/repositories/repo-status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRepositories } from "@/lib/hooks/use-repositories";
import { FolderGit2, type LucideIcon } from "lucide-react";
import Link from "next/link";

interface RepoPickerProps {
  title: string;
  description: string;
  /** Destination prefix; the repo id is appended (e.g. "/bugs" → "/bugs/{id}"). */
  hrefPrefix: string;
  icon?: LucideIcon;
}

/** Shared "choose a repository" grid used by feature index pages. */
export function RepoPicker({ title, description, hrefPrefix, icon = FolderGit2 }: RepoPickerProps) {
  const { data, isLoading } = useRepositories({ page: 1, page_size: 50 });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        <p className="text-muted-foreground">{description}</p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState icon={icon} title="No repositories" description="Add a repository first." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((repo) => (
            <Link key={repo.id} href={`${hrefPrefix}/${repo.id}`}>
              <Card className="transition-colors hover:border-primary/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <CardTitle className="truncate text-base">{repo.name}</CardTitle>
                  <RepoStatusBadge status={repo.status} />
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {repo.primary_language || "—"} · {repo.file_count || 0} files
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
