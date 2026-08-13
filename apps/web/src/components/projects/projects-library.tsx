"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ProjectCard } from "./project-card";
import { ProjectForm } from "./project-form";
import { useProjects } from "@/lib/queries";

export function ProjectsLibrary() {
  const { data: projects, isLoading, error, refetch } = useProjects();
  const [createOpen, setCreateOpen] = useState(false);
  const router = useRouter();

  const NewProjectButton = (
    <Dialog open={createOpen} onOpenChange={setCreateOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="h-8">
          <Plus className="h-3.5 w-3.5" />
          New project
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>
            A project is one building or coordination effort — a B2 prefix
            indexed by its own manifest.
          </DialogDescription>
        </DialogHeader>
        <ProjectForm
          onSuccess={(project) => {
            setCreateOpen(false);
            router.push(`/projects/${project.slug}`);
          }}
          onCancel={() => setCreateOpen(false)}
        />
      </DialogContent>
    </Dialog>
  );

  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
            Building projects archived on Backblaze B2. Ingest IFC models, run the
            IfcOpenShell pipeline, and browse the derived artifacts.
          </p>
        </div>
        {NewProjectButton}
      </div>

      {error ? (
        <Card>
          <CardContent className="p-0">
            <ErrorState error={error} onRetry={() => refetch()} />
          </CardContent>
        </Card>
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : projects && projects.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <ProjectCard key={p.slug} project={p} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={Building2}
              title="No projects yet"
              description="Create a project, ingest an IFC model (or load the sample models), then run the pipeline to fan out geometry, metadata, and analysis onto B2."
              action={NewProjectButton}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
