"use client";

import { FindingsScan } from "@/components/feature/findings/findings-scan";
import { Shield } from "lucide-react";
import { useParams } from "next/navigation";

export default function SecurityDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  return (
    <FindingsScan
      repoId={repoId}
      type="security"
      title="Security Scanner"
      description="Vulnerabilities such as injection, secrets, path traversal, XSS, and weak crypto."
      icon={Shield}
      scoreLabel="Security Score"
    />
  );
}
