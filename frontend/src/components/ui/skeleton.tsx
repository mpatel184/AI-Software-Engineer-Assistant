import { cn } from "@/lib/utils";

/** Pulsing placeholder block used by loading states. */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("skeleton-shimmer rounded-md bg-muted/60", className)}
      {...props}
    />
  );
}

export { Skeleton };
