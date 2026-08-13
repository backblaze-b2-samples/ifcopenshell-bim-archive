import { ArrowUpRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WriteAmplification } from "@ifcopenshell-bim-archive/shared";

export function WriteAmplificationPanel({
  amp,
}: {
  amp: WriteAmplification;
}) {
  const total = amp.source_bytes + amp.artifact_bytes;
  const sourcePct = total > 0 ? (amp.source_bytes / total) * 100 : 0;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-1.5">
          <ArrowUpRight className="h-4 w-4 text-[var(--brand-b2)]" />
          Write amplification
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-semibold tabular-nums">
            {amp.ratio.toFixed(2)}×
          </span>
          <span className="text-sm text-muted-foreground">
            derived bytes vs. source bytes
          </span>
        </div>

        {/* Source vs. artifact split. */}
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-[var(--brand-b2)]/70">
          <div
            className="h-full bg-muted-foreground/40"
            style={{ width: `${sourcePct}%` }}
          />
        </div>
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Source IFC</p>
            <p className="font-mono tabular-nums">{amp.source_human}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Derived artifacts</p>
            <p className="font-mono tabular-nums">{amp.artifact_human}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Total on B2</p>
            <p className="font-mono tabular-nums">{amp.total_human}</p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          A handful of IFC models fan out into geometry bundles, metadata JSON,
          and analysis reports. Backblaze B2 is the single layer holding all of
          it and serving it back via presigned URLs.
        </p>
      </CardContent>
    </Card>
  );
}
