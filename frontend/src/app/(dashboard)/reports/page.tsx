"use client";

import { RepoPicker } from "@/components/feature/repositories/repo-picker";
import { ScrollText } from "lucide-react";

export default function ReportsIndexPage() {
  return (
    <RepoPicker
      title="Reports"
      description="Select a repository to generate and export reports."
      hrefPrefix="/reports"
      icon={ScrollText}
    />
  );
}
