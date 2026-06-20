"use client";

import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { UserCircle2 } from "lucide-react";

export function Topbar() {
  return (
    <header className="flex h-16 items-center justify-between border-b bg-background/80 px-6 backdrop-blur">
      <div className="text-sm text-muted-foreground">
        {/* Breadcrumb / context slot — wired per page in later steps. */}
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button variant="ghost" size="icon" aria-label="Account">
          <UserCircle2 className="size-5" />
        </Button>
      </div>
    </header>
  );
}
