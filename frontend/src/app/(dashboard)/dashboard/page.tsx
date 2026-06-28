"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileCode2, GitBranch, Languages, ShieldAlert, FolderGit2 } from "lucide-react";
import { useRepositories } from "@/lib/hooks/use-repositories";
import { RepoCard } from "@/components/feature/repositories/repo-card";
import { useMemo } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const { data, isLoading } = useRepositories({ page: 1, page_size: 3 });

  const stats = useMemo(() => {
    if (!data) {
      return [
        { label: "Total Files", value: "—", icon: FileCode2 },
        { label: "Languages", value: "—", icon: Languages },
        { label: "Repositories", value: "—", icon: GitBranch },
        { label: "Open Findings", value: "—", icon: ShieldAlert },
      ];
    }

    const repos = data.items;
    const totalFiles = repos.reduce((acc, repo) => acc + (repo.file_count || 0), 0);

    const languages = new Set<string>();
    repos.forEach(repo => {
      if (repo.primary_language) {
        languages.add(repo.primary_language);
      }
    });

    return [
      { label: "Total Files", value: totalFiles > 0 ? totalFiles.toLocaleString() : "0", icon: FileCode2 },
      { label: "Languages", value: languages.size > 0 ? languages.size.toString() : "0", icon: Languages },
      { label: "Repositories", value: data.total.toString(), icon: GitBranch },
      { label: "Open Findings", value: "0", icon: ShieldAlert },
    ];
  }, [data]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Analytics based on your indexed repositories.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </CardTitle>
              <stat.icon className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading ? <span className="animate-pulse text-muted-foreground">...</span> : stat.value}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold tracking-tight">Recent Repositories</h2>
          {data && data.total > 0 && (
            <Button variant="link" asChild>
              <Link href="/repositories">View all</Link>
            </Button>
          )}
        </div>

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="h-48 animate-pulse bg-muted" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((repo) => (
              <RepoCard key={repo.id} repo={repo} />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-10 text-center">
              <FolderGit2 className="mb-4 size-10 text-muted-foreground" />
              <h3 className="mb-1 text-lg font-medium">No repositories found</h3>
              <p className="mb-4 text-sm text-muted-foreground">
                Connect a GitHub repository or upload one to begin analysis, documentation, and chat.
              </p>
              <Button asChild>
                <Link href="/repositories">Add Repository</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
