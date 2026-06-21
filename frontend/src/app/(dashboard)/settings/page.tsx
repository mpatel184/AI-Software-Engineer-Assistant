"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getErrorMessage,
  useChangePassword,
  useCurrentUser,
  useLogout,
  useUpdateProfile,
} from "@/lib/hooks/use-auth";
import { Loader2 } from "lucide-react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function SettingsPage() {
  const { data: user, isLoading } = useCurrentUser();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Manage your profile, password, and preferences.</p>
      </div>

      {isLoading || !user ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          <ProfileCard fullName={user.full_name} email={user.email} role={user.role} />
          <PasswordCard />
          <AppearanceCard />
        </>
      )}
    </div>
  );
}

function ProfileCard({
  fullName,
  email,
  role,
}: {
  fullName: string | null;
  email: string;
  role: string;
}) {
  const update = useUpdateProfile();
  const [name, setName] = useState(fullName ?? "");

  const onSave = () =>
    update.mutate(
      { full_name: name.trim() || null },
      {
        onSuccess: () => toast.success("Profile updated."),
        onError: (e) => toast.error(getErrorMessage(e)),
      },
    );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>Your account details.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" value={email} disabled />
        </div>
        <div className="space-y-2">
          <Label htmlFor="full_name">Full name</Label>
          <Input
            id="full_name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Role:</span>
          <Badge variant="secondary" className="capitalize">{role}</Badge>
        </div>
        <Button onClick={onSave} disabled={update.isPending}>
          {update.isPending && <Loader2 className="size-4 animate-spin" />}
          Save changes
        </Button>
      </CardContent>
    </Card>
  );
}

function PasswordCard() {
  const change = useChangePassword();
  const logout = useLogout();
  const router = useRouter();

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      toast.error("New passwords do not match.");
      return;
    }
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          toast.success("Password changed. Please log in again.");
          logout.mutate(undefined, { onSettled: () => router.push("/login") });
        },
        onError: (e) => toast.error(getErrorMessage(e)),
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change password</CardTitle>
        <CardDescription>
          You will be signed out of all sessions after changing your password.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="space-y-2">
            <Label htmlFor="current">Current password</Label>
            <Input
              id="current"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new">New password</Label>
            <Input
              id="new"
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm">Confirm new password</Label>
            <Input
              id="confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <Button type="submit" disabled={change.isPending}>
            {change.isPending && <Loader2 className="size-4 animate-spin" />}
            Update password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function AppearanceCard() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const options = ["light", "dark", "system"] as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>Choose your preferred theme.</CardDescription>
      </CardHeader>
      <CardContent className="flex gap-2">
        {options.map((opt) => (
          <Button
            key={opt}
            variant={mounted && theme === opt ? "default" : "outline"}
            size="sm"
            className="capitalize"
            onClick={() => setTheme(opt)}
          >
            {opt}
          </Button>
        ))}
      </CardContent>
    </Card>
  );
}
