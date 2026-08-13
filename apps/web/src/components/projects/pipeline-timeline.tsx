import { Check, CircleDashed, Loader2, X } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PIPELINE_STAGE_NAMES } from "@/lib/bim";
import type { PipelineStage, ProjectStatus } from "@ifcopenshell-bim-archive/shared";

function StageIcon({ status }: { status: ProjectStatus }) {
  if (status === "succeeded") return <Check className="h-4 w-4 text-[var(--brand-b2)]" />;
  if (status === "running") return <Loader2 className="h-4 w-4 animate-spin" />;
  if (status === "failed") return <X className="h-4 w-4 text-destructive" />;
  return <CircleDashed className="h-4 w-4 text-muted-foreground" />;
}

export function PipelineTimeline({
  pipeline,
  status,
}: {
  pipeline: PipelineStage[];
  status: ProjectStatus;
}) {
  const stages =
    pipeline.length > 0
      ? pipeline
      : PIPELINE_STAGE_NAMES.map((name) => ({
          name,
          status: "draft" as ProjectStatus,
          detail: "",
        }));

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Pipeline</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <ol className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-2">
          {stages.map((stage, i) => (
            <li key={stage.name} className="flex flex-1 items-center gap-2">
              <div className="flex items-center gap-2">
                <StageIcon status={stage.status} />
                <span className="text-sm font-medium">{stage.name}</span>
              </div>
              {i < stages.length - 1 && (
                <div className="hidden h-px flex-1 bg-border sm:block" />
              )}
            </li>
          ))}
        </ol>
        {status === "failed" && (
          <p className="mt-3 text-xs text-destructive">
            {stages.find((s) => s.detail)?.detail ??
              "The run failed — see the project error."}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
