"use client";

import { SeverityBadge } from "@/components/feature/findings/severity-badge";
import { EmptyState } from "@/components/empty-states/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/lib/hooks/use-auth";
import { useLatestAnalysis, useTriggerAnalysis } from "@/lib/hooks/use-analyses";
import type { AnalysisType, Finding, Severity } from "@/types/api";
import { Loader2, type LucideIcon } from "lucide-react";
import { toast } from "sonner";

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

interface FindingsScanProps {
  repoId: string;
  type: Extract<AnalysisType, "bugs" | "security">;
  title: string;
  description: string;
  icon: LucideIcon;
  /** Label for the score card (e.g. "Code Health", "Security Score"). */
  scoreLabel: string;
}

export function FindingsScan({
  repoId,
  type,
  title,
  description,
  icon: Icon,
  scoreLabel,
}: FindingsScanProps) {
  const { data: scan, isLoading } = useLatestAnalysis(repoId, type);
  const trigger = useTriggerAnalysis(repoId, type);

  const running = scan?.status === "queued" || scan?.status === "running";

  const onScan = () =>
    trigger.mutate(undefined, {
      onSuccess: () => toast.success("Scan started."),
      onError: (e) => toast.error(getErrorMessage(e)),
    });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="text-muted-foreground">{description}</p>
        </div>
        <Button onClick={onScan} disabled={trigger.isPending || running}>
          {(trigger.isPending || running) && <Loader2 className="size-4 animate-spin" />}
          {running ? "Scanning…" : scan ? "Re-scan" : "Run scan"}
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : !scan ? (
        <EmptyState
          icon={Icon}
          title="No scan yet"
          description="Run a scan to analyze this repository. It must be fully indexed first."
          action={<Button onClick={onScan} disabled={trigger.isPending}>Run scan</Button>}
        />
      ) : scan.status === "failed" ? (
        <EmptyState
          icon={Icon}
          title="Scan failed"
          description={scan.error_message || "Something went wrong. Try running it again."}
        />
      ) : running ? (
        <EmptyState
          icon={Icon}
          title="Scan in progress"
          description="Claude is reviewing the source. This page updates automatically."
        />
      ) : (
        <ScanResult scan={scan} scoreLabel={scoreLabel} icon={Icon} />
      )}
    </div>
  );
}

function ScanResult({
  scan,
  scoreLabel,
  icon: Icon,
}: {
  scan: NonNullable<ReturnType<typeof useLatestAnalysis>["data"]>;
  scoreLabel: string;
  icon: LucideIcon;
}) {
  const findings: Finding[] = scan.summary.findings ?? [];
  const counts = scan.metrics.counts ?? ({} as Record<Severity, number>);
  const sorted = [...findings].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{scoreLabel}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{scan.score ?? "—"}</div>
          </CardContent>
        </Card>
        {SEVERITY_ORDER.map((sev) => (
          <Card key={sev}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium capitalize text-muted-foreground">{sev}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{counts[sev] ?? 0}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {scan.summary.overview && (
        <Card>
          <CardHeader>
            <CardTitle>Overview</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-relaxed text-muted-foreground">
            {scan.summary.overview}
          </CardContent>
        </Card>
      )}

      {sorted.length === 0 ? (
        <EmptyState icon={Icon} title="No issues found" description="The scan completed with no findings." />
      ) : (
        <div className="space-y-4">
          {sorted.map((f, i) => (
            <Card key={`${f.file_path}-${i}`}>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <CardTitle className="text-base">{f.title}</CardTitle>
                  <SeverityBadge severity={f.severity} />
                </div>
                <CardDescription>
                  <span className="capitalize">{f.category.replace(/_/g, " ")}</span>
                  {f.file_path && (
                    <>
                      {" · "}
                      <code className="text-xs">
                        {f.file_path}
                        {f.line ? `:${f.line}` : ""}
                      </code>
                    </>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p>{f.description}</p>
                {f.recommendation && (
                  <div>
                    <h4 className="font-semibold">Recommendation</h4>
                    <p className="text-muted-foreground">{f.recommendation}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
