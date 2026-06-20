import { Sparkles } from "lucide-react";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Sparkles className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">AI Software Engineer Assistant</h1>
            <p className="text-sm text-muted-foreground">
              Analyze, document, and chat with any codebase.
            </p>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}
