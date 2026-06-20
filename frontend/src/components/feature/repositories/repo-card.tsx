"use client";

import { RepoStatusBadge } from "@/components/feature/repositories/repo-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDeleteRepository, useReindexRepository } from "@/lib/hooks/use-repositories";
import type { Repository } from "@/types/api";
import { FileCode2, Github, MoreVertical, RefreshCw, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";

function formatBytes(bytes: number): string {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(1)} ${units[i]}`;
}

export function RepoCard({ repo }: { repo: Repository }) {
  const reindex = useReindexRepository();
  const remove = useDeleteRepository();

  return (
    <Card className="flex flex-col">
      <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
        <div className="flex items-center gap-2 overflow-hidden">
          {repo.source === "github" ? (
            <Github className="size-4 shrink-0 text-muted-foreground" />
          ) : (
            <Upload className="size-4 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate font-semibold">{repo.name}</span>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="size-7">
              <MoreVertical className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() =>
                reindex.mutate(repo.id, {
                  onSuccess: () => toast.success("Re-indexing started."),
                  onError: () => toast.error("Could not start re-indexing."),
                })
              }
            >
              <RefreshCw className="size-4" /> Re-index
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() =>
                remove.mutate(repo.id, {
                  onSuccess: () => toast.success("Repository deleted."),
                  onError: () => toast.error("Could not delete repository."),
                })
              }
            >
              <Trash2 className="size-4" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>

      <CardContent className="flex-1 space-y-3">
        <RepoStatusBadge status={repo.status} />
        {repo.status === "failed" && repo.error_message && (
          <p className="line-clamp-2 text-xs text-destructive">{repo.error_message}</p>
        )}
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div>
            <p className="text-muted-foreground">Files</p>
            <p className="font-medium">{repo.file_count || "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Lines</p>
            <p className="font-medium">{repo.total_lines.toLocaleString() || "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Size</p>
            <p className="font-medium">{formatBytes(repo.size_bytes)}</p>
          </div>
        </div>
        {repo.primary_language && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <FileCode2 className="size-3.5" />
            {repo.primary_language}
          </div>
        )}
      </CardContent>

      <CardFooter>
        <Button variant="outline" size="sm" className="w-full" disabled={repo.status !== "ready"} asChild>
          <a href={`/chat/${repo.id}`}>Open chat</a>
        </Button>
      </CardFooter>
    </Card>
  );
}
