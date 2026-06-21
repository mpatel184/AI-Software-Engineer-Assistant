"use client";

import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/lib/hooks/use-auth";
import { useGenerateTests, useRepoFiles } from "@/lib/hooks/use-tests";
import { cn } from "@/lib/utils";
import { Copy, FlaskConical, Loader2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";

export default function TestsDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const { data, isLoading } = useRepoFiles(repoId);
  const generate = useGenerateTests(repoId);

  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const files = useMemo(() => {
    const all = data?.files ?? [];
    const q = query.trim().toLowerCase();
    return q ? all.filter((f) => f.toLowerCase().includes(q)) : all;
  }, [data, query]);

  const onGenerate = () => {
    if (!selected) return;
    generate.mutate(selected, {
      onSuccess: () => toast.success("Tests generated."),
      onError: (e) => toast.error(getErrorMessage(e)),
    });
  };

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard.");
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Test Generator</h1>
        <p className="text-muted-foreground">
          Pick a source file and generate a unit-test suite for it.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">Source files</CardTitle>
            <CardDescription>Select a file to test.</CardDescription>
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
            <Button onClick={onGenerate} disabled={!selected || generate.isPending}>
              {generate.isPending && <Loader2 className="size-4 animate-spin" />}
              Generate tests
            </Button>
          </div>

          {generate.isPending ? (
            <Skeleton className="h-96 w-full" />
          ) : generate.data ? (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <CardTitle className="text-base">{generate.data.test_file_path}</CardTitle>
                    <CardDescription>{generate.data.notes}</CardDescription>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant="secondary">{generate.data.framework}</Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copy(generate.data!.test_code)}
                    >
                      <Copy className="size-4" /> Copy
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <pre className="max-h-[600px] overflow-auto rounded-lg bg-muted p-4 text-xs leading-relaxed">
                  <code>{generate.data.test_code}</code>
                </pre>
              </CardContent>
            </Card>
          ) : (
            <EmptyState
              icon={FlaskConical}
              title="No tests generated yet"
              description="Choose a file from the list and click Generate tests."
            />
          )}
        </div>
      </div>
    </div>
  );
}
