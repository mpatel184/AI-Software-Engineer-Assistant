"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getErrorMessage } from "@/lib/hooks/use-auth";
import { useCreateRepository, useUploadRepository } from "@/lib/hooks/use-repositories";
import { Github, Loader2, Plus, Upload } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export function AddRepositoryDialog() {
  const [open, setOpen] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [repoName, setRepoName] = useState("");
  const [uploadName, setUploadName] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const create = useCreateRepository();
  const upload = useUploadRepository();

  const reset = () => {
    setGithubUrl("");
    setRepoName("");
    setUploadName("");
    setFile(null);
  };

  const onGitHub = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(
      { github_url: githubUrl, name: repoName || undefined },
      {
        onSuccess: () => {
          toast.success("Repository added — indexing started.");
          setOpen(false);
          reset();
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  };

  const onUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return toast.error("Please choose a .zip file.");
    upload.mutate(
      { name: uploadName || file.name.replace(/\.zip$/i, ""), file },
      {
        onSuccess: () => {
          toast.success("Upload received — indexing started.");
          setOpen(false);
          reset();
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="size-4" /> Add repository
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add a repository</DialogTitle>
          <DialogDescription>
            Connect a public GitHub repo or upload a .zip of your codebase.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="github">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="github">
              <Github className="mr-2 size-4" /> GitHub
            </TabsTrigger>
            <TabsTrigger value="upload">
              <Upload className="mr-2 size-4" /> Upload
            </TabsTrigger>
          </TabsList>

          <TabsContent value="github">
            <form onSubmit={onGitHub} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="github-url">GitHub URL</Label>
                <Input
                  id="github-url"
                  required
                  placeholder="https://github.com/owner/repo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="repo-name">Display name (optional)</Label>
                <Input
                  id="repo-name"
                  placeholder="My project"
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={create.isPending}>
                {create.isPending && <Loader2 className="size-4 animate-spin" />}
                Connect & index
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="upload">
            <form onSubmit={onUpload} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="upload-name">Display name (optional)</Label>
                <Input
                  id="upload-name"
                  placeholder="My project"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="zip">ZIP file</Label>
                <Input
                  id="zip"
                  type="file"
                  accept=".zip"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={upload.isPending}>
                {upload.isPending && <Loader2 className="size-4 animate-spin" />}
                Upload & index
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
