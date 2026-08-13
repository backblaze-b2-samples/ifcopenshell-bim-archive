"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Layers,
  Pencil,
  Play,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ProjectStatusBadge } from "./project-status";
import { ProjectForm } from "./project-form";
import { ProjectIngest } from "./project-ingest";
import { PipelineTimeline } from "./pipeline-timeline";
import { BimStatsPanel } from "./bim-stats";
import { WriteAmplificationPanel } from "./write-amplification-panel";
import { AssetExplorer } from "./asset-explorer";
import { DownstreamSnippet } from "./downstream-snippet";
import { useDeleteProject, useProject, useRunProject } from "@/lib/queries";
import { disciplineLabel, geometryDetailLabel } from "@/lib/bim";

export function ProjectDetail({ slug }: { slug: string }) {
  const { data: project, isLoading, error, refetch } = useProject(slug);
  const runMutation = useRunProject(slug);
  const deleteMutation = useDeleteProject();
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  if (isLoading || !project) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const hasModels = project.models.length > 0;
  const running = project.status === "running" || runMutation.isPending;

  const runPipeline = async () => {
    try {
      await runMutation.mutateAsync();
      toast.success("Pipeline finished");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Run failed");
    }
  };

  const onDelete = async () => {
    try {
      await deleteMutation.mutateAsync(slug);
      toast.success(`Deleted "${project.name}"`);
      router.push("/projects");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete");
    }
  };

  return (
    <div className="space-y-6">
      <div className="animate-fade-in space-y-4 border-b border-border pb-5">
        <Link
          href="/projects"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> All projects
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="page-title">{project.name}</h1>
              <ProjectStatusBadge status={project.status} />
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground">
              {disciplineLabel(project.discipline)} ·{" "}
              {geometryDetailLabel(project.geometry_detail)} geometry detail ·{" "}
              <code className="text-xs">projects/{project.slug}/</code>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
              <Pencil className="h-3.5 w-3.5" /> Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </Button>
            <Button size="sm" onClick={runPipeline} disabled={!hasModels || running}>
              <Play className="h-3.5 w-3.5" />
              {running ? "Running..." : "Run pipeline"}
            </Button>
          </div>
        </div>
      </div>

      {project.status === "failed" && project.error && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>Last run failed</AlertTitle>
          <AlertDescription>{project.error}</AlertDescription>
        </Alert>
      )}

      {/* Source models */}
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">
            Source models ({project.models.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          {hasModels ? (
            <div className="divide-y divide-border rounded-md border border-border">
              {project.models.map((m) => (
                <div
                  key={m.key}
                  className="flex items-center justify-between gap-3 px-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm">{m.filename}</p>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {m.key}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <Badge variant="outline">{disciplineLabel(m.discipline)}</Badge>
                    <span className="font-mono text-xs tabular-nums text-muted-foreground">
                      {m.size_human}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Layers}
              title="No models ingested"
              description="Load the sample models or upload your own .ifc below, then run the pipeline."
            />
          )}
        </CardContent>
      </Card>

      <ProjectIngest slug={slug} />

      <PipelineTimeline pipeline={project.pipeline} status={project.status} />

      {project.stats && <BimStatsPanel stats={project.stats} />}

      {project.write_amplification &&
        project.write_amplification.source_bytes > 0 && (
          <WriteAmplificationPanel amp={project.write_amplification} />
        )}

      <AssetExplorer slug={slug} />

      <DownstreamSnippet slug={slug} />

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit project</DialogTitle>
            <DialogDescription>
              Update the name, discipline, or geometry detail.
            </DialogDescription>
          </DialogHeader>
          <ProjectForm
            project={project}
            onSuccess={() => setEditOpen(false)}
            onCancel={() => setEditOpen(false)}
          />
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete “{project.name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes the project and every object under{" "}
              <code>projects/{project.slug}/</code> (source models and all
              derived artifacts). This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                onDelete();
              }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete project"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
