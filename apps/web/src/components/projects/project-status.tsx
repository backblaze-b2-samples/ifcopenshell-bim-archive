import { Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { STATUS_META } from "@/lib/bim";
import type { ProjectStatus } from "@ifcopenshell-bim-archive/shared";

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant={meta.variant} className="gap-1">
      {status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
      {meta.label}
    </Badge>
  );
}
