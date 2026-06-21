"use client";

import { RepoPicker } from "@/components/feature/repositories/repo-picker";
import { MessageSquare } from "lucide-react";

export default function ChatIndexPage() {
  return (
    <RepoPicker
      title="Chat"
      description="Select a repository to ask questions about its codebase."
      hrefPrefix="/chat"
      icon={MessageSquare}
    />
  );
}
