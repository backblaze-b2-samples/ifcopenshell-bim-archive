import { Box, DoorOpen, Layers, TriangleAlert } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { disciplineLabel } from "@/lib/bim";
import type { BimStats } from "@ifcopenshell-bim-archive/shared";

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Box;
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="stat-value mt-1">{value.toLocaleString()}</div>
    </div>
  );
}

export function BimStatsPanel({ stats }: { stats: BimStats }) {
  const types = Object.entries(stats.type_counts).sort((a, b) => b[1] - a[1]);
  const disciplines = Object.entries(stats.discipline_counts).sort(
    (a, b) => b[1] - a[1]
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Model insight</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5 p-5">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric icon={Box} label="Elements" value={stats.element_count} />
          <Metric icon={DoorOpen} label="Spaces" value={stats.space_count} />
          <Metric icon={Layers} label="Meshes" value={stats.mesh_count} />
          <Metric
            icon={TriangleAlert}
            label="Clash candidates"
            value={stats.clash_candidate_count}
          />
        </div>

        {types.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Quantity take-off (by IfcType)
            </p>
            <div className="divide-y divide-border rounded-md border border-border">
              {types.map(([type, count]) => (
                <div
                  key={type}
                  className="flex items-center justify-between px-3 py-1.5 text-sm"
                >
                  <span className="font-mono text-xs">{type}</span>
                  <span className="font-mono tabular-nums">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {disciplines.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Elements by discipline
            </p>
            <div className="flex flex-wrap gap-2">
              {disciplines.map(([d, count]) => (
                <span
                  key={d}
                  className="rounded-full border border-border px-2.5 py-1 text-xs"
                >
                  {disciplineLabel(d)}:{" "}
                  <span className="font-mono tabular-nums">{count}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
