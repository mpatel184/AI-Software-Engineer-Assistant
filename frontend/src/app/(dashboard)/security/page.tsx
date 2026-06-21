"use client";

import { RepoPicker } from "@/components/feature/repositories/repo-picker";
import { Shield } from "lucide-react";

export default function SecurityIndexPage() {
  return (
    <RepoPicker
      title="Security"
      description="Select a repository to scan for security vulnerabilities."
      hrefPrefix="/security"
      icon={Shield}
    />
  );
}
