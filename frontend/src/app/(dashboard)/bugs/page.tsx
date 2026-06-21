"use client";

import { RepoPicker } from "@/components/feature/repositories/repo-picker";
import { Bug } from "lucide-react";

export default function BugsIndexPage() {
  return (
    <RepoPicker
      title="Bug Detection"
      description="Select a repository to scan for bugs, code smells, and dead code."
      hrefPrefix="/bugs"
      icon={Bug}
    />
  );
}
