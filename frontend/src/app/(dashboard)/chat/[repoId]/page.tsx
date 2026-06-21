"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/lib/hooks/use-auth";
import { useAskQuestion, useChatHistory, useClearChat } from "@/lib/hooks/use-chat";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/api";
import { Loader2, MessageSquare, Send, Trash2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

const SUGGESTIONS = [
  "How does authentication work?",
  "Where are the API endpoints defined?",
  "Explain the database schema.",
  "What is the overall architecture?",
];

export default function ChatDetailPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const { data: history, isLoading } = useChatHistory(repoId);
  const ask = useAskQuestion(repoId);
  const clear = useClearChat(repoId);

  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, ask.isPending]);

  const send = (question: string) => {
    const q = question.trim();
    if (!q || ask.isPending) return;
    setInput("");
    ask.mutate(q, { onError: (e) => toast.error(getErrorMessage(e)) });
  };

  const empty = !isLoading && (history?.length ?? 0) === 0;

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Repository Chat</h1>
          <p className="text-muted-foreground">Answers are grounded in this repository&apos;s code.</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={clear.isPending || empty}
          onClick={() => clear.mutate(undefined, { onError: (e) => toast.error(getErrorMessage(e)) })}
        >
          <Trash2 className="size-4" /> Clear
        </Button>
      </div>

      <Card className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-16 w-2/3" />
            <Skeleton className="ml-auto h-16 w-2/3" />
          </div>
        ) : empty ? (
          <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
            <div className="flex flex-col items-center gap-2">
              <MessageSquare className="size-10 text-muted-foreground" />
              <p className="text-muted-foreground">Ask anything about this repository.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <Button key={s} variant="secondary" size="sm" onClick={() => send(s)}>
                  {s}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {history!.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {ask.isPending && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Thinking…
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </Card>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <Input
          placeholder="Ask a question about the code…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={ask.isPending}
        />
        <Button type="submit" disabled={!input.trim() || ask.isPending}>
          {ask.isPending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
        </Button>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-3 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted",
        )}
      >
        <pre className="whitespace-pre-wrap break-words font-sans leading-relaxed">
          {message.content}
        </pre>
        {message.sources.length > 0 && (
          <div className="mt-3 border-t border-border/50 pt-2">
            <p className="mb-1 text-xs font-semibold opacity-70">Sources</p>
            <ul className="space-y-0.5">
              {message.sources.map((s, i) => (
                <li key={`${s.file_path}-${i}`} className="text-xs opacity-70">
                  <code>
                    {s.file_path}:{s.start_line}-{s.end_line}
                  </code>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
