"use client";

import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/lib/hooks/use-auth";
import { useLatestAnalysis, useTriggerAnalysis } from "@/lib/hooks/use-analyses";
import { Loader2, Telescope } from "lucide-react";
import { useParams } from "next/navigation";
import { toast } from "sonner";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}

export default function AnalysisDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const { data: analysis, isLoading } = useLatestAnalysis(repoId);
  const trigger = useTriggerAnalysis(repoId);

  const running = analysis?.status === "queued" || analysis?.status === "running";

  const onAnalyze = () =>
    trigger.mutate(undefined, {
      onSuccess: () => toast.success("Analysis started."),
      onError: (e) => toast.error(getErrorMessage(e)),
    });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Architecture Analysis</h1>
          <p className="text-muted-foreground">AI-generated overview, metrics, and dependencies.</p>
        </div>
        <Button onClick={onAnalyze} disabled={trigger.isPending || running}>
          {(trigger.isPending || running) && <Loader2 className="size-4 animate-spin" />}
          {running ? "Analyzing…" : analysis ? "Re-analyze" : "Run analysis"}
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : !analysis ? (
        <EmptyState
          icon={Telescope}
          title="No analysis yet"
          description="Run an analysis to generate an architecture overview and metrics for this repository."
          action={<Button onClick={onAnalyze} disabled={trigger.isPending}>Run analysis</Button>}
        />
      ) : analysis.status === "failed" ? (
        <EmptyState
          icon={Telescope}
          title="Analysis failed"
          description={analysis.error_message || "Something went wrong. Try running it again."}
        />
      ) : running ? (
        <EmptyState
          icon={Telescope}
          title="Analysis in progress"
          description="Computing metrics and generating the architecture overview. This page updates automatically."
        />
      ) : (
        <AnalysisResult analysis={analysis} />
      )}
    </div>
  );
}

function AnalysisResult({ analysis }: { analysis: NonNullable<ReturnType<typeof useLatestAnalysis>["data"]> }) {
  const m = analysis.metrics;
  const s = analysis.summary;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Health Score" value={analysis.score ?? "—"} />
        <Stat label="Files" value={m.file_count ?? "—"} />
        <Stat label="Lines" value={(m.total_lines ?? 0).toLocaleString()} />
        <Stat label="Doc Coverage" value={`${m.doc_coverage_pct ?? 0}%`} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Project Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-relaxed">
          <p>{s.project_summary}</p>
          <div>
            <h3 className="mb-1 font-semibold">Architecture</h3>
            <p className="text-muted-foreground">{s.architecture_overview}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Technology Stack</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {(s.tech_stack ?? []).map((t) => (
              <Badge key={t} variant="secondary">{t}</Badge>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Languages</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(m.languages ?? {}).map(([lang, pct]) => (
              <div key={lang}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{lang}</span>
                  <span className="text-muted-foreground">{pct}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Dependencies</CardTitle>
            <CardDescription>Declared in manifest files.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {Object.entries(m.dependencies ?? {}).map(([eco, deps]) => (
              <div key={eco}>
                <h4 className="font-semibold capitalize">{eco}</h4>
                <p className="text-muted-foreground">
                  {deps.length ? deps.slice(0, 20).join(", ") : "—"}
                  {deps.length > 20 ? ` +${deps.length - 20} more` : ""}
                </p>
              </div>
            ))}
            {Object.keys(m.dependencies ?? {}).length === 0 && (
              <p className="text-muted-foreground">No dependency manifests found.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Folder Explanation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(s.folder_explanation ?? []).map((f) => (
              <div key={f.path}>
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{f.path}</code>
                <p className="mt-0.5 text-muted-foreground">{f.purpose}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Complexity Hotspots</CardTitle>
          <CardDescription>
            Avg {m.avg_complexity ?? 0} · Max {m.max_complexity ?? 0}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-1 text-sm">
            {(m.complexity_hotspots ?? []).slice(0, 8).map((h) => (
              <div key={h.file_path} className="flex items-center justify-between gap-4">
                <code className="truncate text-xs">{h.file_path}</code>
                <Badge variant={h.estimated_complexity > 20 ? "destructive" : "secondary"}>
                  {h.estimated_complexity}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
