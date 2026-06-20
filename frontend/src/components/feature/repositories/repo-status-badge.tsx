import { Badge } from "@/components/ui/badge";
import type { RepoStatus } from "@/types/api";
import { Loader2 } from "lucide-react";

const CONFIG: Record<
  RepoStatus,
  { label: string; variant: "default" | "success" | "warning" | "destructive"; spin?: boolean }
> = {
  pending: { label: "Pending", variant: "warning", spin: true },
  cloning: { label: "Cloning", variant: "warning", spin: true },
  indexing: { label: "Indexing", variant: "warning", spin: true },
  ready: { label: "Ready", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
};

export function RepoStatusBadge({ status }: { status: RepoStatus }) {
  const config = CONFIG[status];
  return (
    <Badge variant={config.variant} className="gap-1">
      {config.spin && <Loader2 className="size-3 animate-spin" />}
      {config.label}
    </Badge>
  );
}
