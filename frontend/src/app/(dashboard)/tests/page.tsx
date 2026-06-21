"use client";

import { RepoPicker } from "@/components/feature/repositories/repo-picker";
import { FlaskConical } from "lucide-react";

export default function TestsIndexPage() {
  return (
    <RepoPicker
      title="Test Generator"
      description="Select a repository to generate unit tests for its source files."
      hrefPrefix="/tests"
      icon={FlaskConical}
    />
  );
}
