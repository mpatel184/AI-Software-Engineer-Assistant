"use client";

import { RepoPicker } from "@/components/feature/repositories/repo-picker";
import { Wand2 } from "lucide-react";

export default function RefactoringIndexPage() {
  return (
    <RepoPicker
      title="Refactoring"
      description="Select a repository to get refactoring suggestions for its files."
      hrefPrefix="/refactoring"
      icon={Wand2}
    />
  );
}
