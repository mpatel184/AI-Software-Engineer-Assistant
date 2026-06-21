"use client";

import { FindingsScan } from "@/components/feature/findings/findings-scan";
import { Bug } from "lucide-react";
import { useParams } from "next/navigation";

export default function BugsDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  return (
    <FindingsScan
      repoId={repoId}
      type="bugs"
      title="Bug Detection"
      description="Potential bugs, code smells, performance issues, duplication, and dead code."
      icon={Bug}
      scoreLabel="Code Health"
    />
  );
}
