"use client";

import { AddRepositoryDialog } from "@/components/feature/repositories/add-repository-dialog";
import { RepoCard } from "@/components/feature/repositories/repo-card";
import { EmptyState } from "@/components/empty-states/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useRepositories } from "@/lib/hooks/use-repositories";
import { FolderGit2 } from "lucide-react";
import { useState } from "react";

export default function RepositoriesPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useRepositories({ page, page_size: 12, search: search || undefined });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Repositories</h1>
          <p className="text-muted-foreground">Connect a codebase to analyze, document, and chat with it.</p>
        </div>
        <AddRepositoryDialog />
      </div>

      <Input
        placeholder="Search repositories…"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        className="max-w-sm"
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-56 w-full" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={FolderGit2}
          title="Couldn’t load repositories"
          description="Something went wrong while fetching your repositories. Please try again."
        />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={FolderGit2}
          title="No repositories yet"
          description="Add your first repository from GitHub or upload a .zip to get started."
          action={<AddRepositoryDialog />}
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((repo) => (
              <RepoCard key={repo.id} repo={repo} />
            ))}
          </div>

          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-4">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {data.page} of {data.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
