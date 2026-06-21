"use client";

import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/lib/hooks/use-auth";
import {
  downloadReportPdf,
  useGenerateReport,
  useReport,
  useReports,
} from "@/lib/hooks/use-reports";
import type { ReportType } from "@/types/api";
import { Download, Loader2, ScrollText } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

const TYPES: { type: ReportType; label: string }[] = [
  { type: "full", label: "Full" },
  { type: "analysis", label: "Architecture" },
  { type: "bugs", label: "Bugs" },
  { type: "security", label: "Security" },
];

export default function ReportsDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const { data: reports, isLoading } = useReports(repoId);
  const generate = useGenerateReport(repoId);

  const [type, setType] = useState<ReportType>("full");
  const [selected, setSelected] = useState<string | null>(null);
  const { data: report } = useReport(repoId, selected);
  const [downloading, setDownloading] = useState(false);

  const onGenerate = () =>
    generate.mutate(type, {
      onSuccess: (r) => {
        setSelected(r.id);
        toast.success("Report generated.");
      },
      onError: (e) => toast.error(getErrorMessage(e)),
    });

  const onDownload = async () => {
    if (!report) return;
    setDownloading(true);
    try {
      await downloadReportPdf(repoId, report.id, report.title);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
        <p className="text-muted-foreground">
          Generate an aggregated report from this repository&apos;s analyses and export it as PDF.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Generate a report</CardTitle>
          <CardDescription>Pick a report type. Run analysis and scans first for full content.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2">
          {TYPES.map((t) => (
            <Button
              key={t.type}
              variant={type === t.type ? "default" : "outline"}
              size="sm"
              onClick={() => setType(t.type)}
            >
              {t.label}
            </Button>
          ))}
          <Button className="ml-auto" onClick={onGenerate} disabled={generate.isPending}>
            {generate.isPending && <Loader2 className="size-4 animate-spin" />}
            Generate
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">History</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)
            ) : (reports?.length ?? 0) === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">No reports yet.</p>
            ) : (
              reports!.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setSelected(r.id)}
                  className={`flex w-full items-center justify-between gap-2 rounded px-2 py-2 text-left text-sm transition-colors hover:bg-muted ${
                    selected === r.id ? "bg-muted" : ""
                  }`}
                >
                  <span className="truncate">{r.title}</span>
                  <Badge variant="secondary" className="shrink-0 capitalize">{r.type}</Badge>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <div>
          {!report ? (
            <EmptyState
              icon={ScrollText}
              title="No report selected"
              description="Generate a report or select one from the history to preview it."
            />
          ) : (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-4">
                  <CardTitle className="text-base">{report.title}</CardTitle>
                  <Button size="sm" variant="outline" onClick={onDownload} disabled={downloading}>
                    {downloading ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
                    PDF
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <pre className="max-h-[600px] overflow-auto whitespace-pre-wrap break-words font-sans text-sm leading-relaxed">
                  {report.content}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
