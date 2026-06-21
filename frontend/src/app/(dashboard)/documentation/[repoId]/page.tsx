"use client";

import { EmptyState } from "@/components/empty-states/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getErrorMessage } from "@/lib/hooks/use-auth";
import { useDocument, useDocuments, useGenerateDocument } from "@/lib/hooks/use-documents";
import type { DocumentType } from "@/types/api";
import { FileText, Loader2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

const DOC_TYPES: { type: DocumentType; label: string }[] = [
  { type: "readme", label: "README" },
  { type: "api_docs", label: "API Docs" },
  { type: "function_docs", label: "Functions" },
  { type: "class_docs", label: "Classes" },
];

export default function DocumentationDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const [active, setActive] = useState<DocumentType>("readme");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Documentation</h1>
        <p className="text-muted-foreground">
          Generate AI-written docs grounded in this repository&apos;s source.
        </p>
      </div>

      <Tabs value={active} onValueChange={(v) => setActive(v as DocumentType)}>
        <TabsList>
          {DOC_TYPES.map((d) => (
            <TabsTrigger key={d.type} value={d.type}>
              {d.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {DOC_TYPES.map((d) => (
          <TabsContent key={d.type} value={d.type}>
            <DocPanel repoId={repoId} type={d.type} label={d.label} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

function DocPanel({ repoId, type, label }: { repoId: string; type: DocumentType; label: string }) {
  const { data: list, isLoading } = useDocuments(repoId);
  const summary = list?.find((d) => d.type === type) ?? null;
  const { data: doc } = useDocument(repoId, summary ? summary.id : null);
  const generate = useGenerateDocument(repoId);

  const status = doc?.status ?? summary?.status;
  const running = status === "queued" || status === "running";

  const onGenerate = () =>
    generate.mutate(type, {
      onSuccess: () => toast.success(`Generating ${label}…`),
      onError: (e) => toast.error(getErrorMessage(e)),
    });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={onGenerate} disabled={generate.isPending || running}>
          {(generate.isPending || running) && <Loader2 className="size-4 animate-spin" />}
          {running ? "Generating…" : summary ? "Regenerate" : "Generate"}
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : !summary ? (
        <EmptyState
          icon={FileText}
          title={`No ${label} yet`}
          description="Generate documentation to view it here. The repository must be fully indexed."
        />
      ) : status === "failed" ? (
        <EmptyState
          icon={FileText}
          title="Generation failed"
          description={summary.error_message || "Something went wrong. Try generating again."}
        />
      ) : running ? (
        <EmptyState
          icon={FileText}
          title="Generating documentation"
          description="Claude is writing the documentation. This page updates automatically."
        />
      ) : doc ? (
        <Card>
          <CardContent className="pt-6">
            <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed">
              {doc.content}
            </pre>
          </CardContent>
        </Card>
      ) : (
        <Skeleton className="h-64 w-full" />
      )}
    </div>
  );
}
