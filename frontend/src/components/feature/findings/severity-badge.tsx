import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Severity } from "@/types/api";

const STYLES: Record<Severity, string> = {
  critical: "border-transparent bg-red-600 text-white",
  high: "border-transparent bg-orange-500 text-white",
  medium: "border-transparent bg-amber-500 text-black",
  low: "border-transparent bg-yellow-400 text-black",
  info: "border-transparent bg-sky-500 text-white",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge className={cn("uppercase", STYLES[severity] ?? "")}>{severity}</Badge>
  );
}
