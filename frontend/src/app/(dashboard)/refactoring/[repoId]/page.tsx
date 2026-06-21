"use client";

import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/lib/hooks/use-auth";
import { useRefactoringFiles, useSuggestRefactorings } from "@/lib/hooks/use-refactoring";
import { cn } from "@/lib/utils";
import type { RefactoringSuggestion } from "@/types/api";
import { Loader2, Wand2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";

const IMPACT_STYLE: Record<RefactoringSuggestion["impact"], string> = {
  high: "border-transparent bg-orange-500 text-white",
  medium: "border-transparent bg-amber-500 text-black",
  low: "border-transparent bg-sky-500 text-white",
};

export default function RefactoringDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const { data, isLoading } = useRefactoringFiles(repoId);
  const suggest = useSuggestRefactorings(repoId);

  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const files = useMemo(() => {
    const all = data?.files ?? [];
    const q = query.trim().toLowerCase();
    return q ? all.filter((f) => f.toLowerCase().includes(q)) : all;
  }, [data, query]);

  const onSuggest = () => {
    if (!selected) return;
    suggest.mutate(selected, {
      onSuccess: () => toast.success("Suggestions ready."),
      onError: (e) => toast.error(getErrorMessage(e)),
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Refactoring</h1>
        <p className="text-muted-foreground">
          Pick a source file to get behavior-preserving refactoring suggestions.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">Source files</CardTitle>
            <CardDescription>Select a file to analyze.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="Filter files…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-7 w-full" />
                ))}
              </div>
            ) : (
              <div className="max-h-[480px] space-y-0.5 overflow-y-auto">
                {files.map((f) => (
                  <button
                    key={f}
                    onClick={() => setSelected(f)}
                    className={cn(
                      "block w-full truncate rounded px-2 py-1 text-left text-xs transition-colors hover:bg-muted",
                      selected === f && "bg-muted font-medium",
                    )}
                    title={f}
                  >
                    {f}
                  </button>
                ))}
                {files.length === 0 && (
                  <p className="px-2 py-4 text-center text-xs text-muted-foreground">
                    No files match.
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <code className="truncate text-sm text-muted-foreground">
              {selected || "No file selected"}
            </code>
            <Button onClick={onSuggest} disabled={!selected || suggest.isPending}>
              {suggest.isPending && <Loader2 className="size-4 animate-spin" />}
              Suggest refactorings
            </Button>
          </div>

          {suggest.isPending ? (
            <Skeleton className="h-96 w-full" />
          ) : suggest.data ? (
            <div className="space-y-4">
              {suggest.data.summary && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm leading-relaxed text-muted-foreground">
                    {suggest.data.summary}
                  </CardContent>
                </Card>
              )}
              {suggest.data.suggestions.length === 0 ? (
                <EmptyState
                  icon={Wand2}
                  title="No suggestions"
                  description="This file looks good — no refactorings were proposed."
                />
              ) : (
                suggest.data.suggestions.map((s, i) => (
                  <Card key={`${s.title}-${i}`}>
                    <CardHeader>
                      <div className="flex items-start justify-between gap-4">
                        <CardTitle className="text-base">{s.title}</CardTitle>
                        <Badge className={cn("uppercase", IMPACT_STYLE[s.impact])}>{s.impact}</Badge>
                      </div>
                      <CardDescription>
                        <span className="capitalize">{s.category.replace(/_/g, " ")}</span>
                        {s.line ? <> · line {s.line}</> : null}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">
                      <p>{s.rationale}</p>
                      {s.suggested_change && (
                        <pre className="overflow-auto rounded-lg bg-muted p-3 text-xs leading-relaxed">
                          <code>{s.suggested_change}</code>
                        </pre>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          ) : (
            <EmptyState
              icon={Wand2}
              title="No suggestions yet"
              description="Choose a file and click Suggest refactorings."
            />
          )}
        </div>
      </div>
    </div>
  );
}
