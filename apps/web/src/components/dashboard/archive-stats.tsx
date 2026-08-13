"use client";

import { ArrowUpRight, Boxes, Building2, FileStack } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useProjectStats } from "@/lib/queries";

/**
 * Archive-wide BIM rollup for the dashboard: project/model/artifact counts and
 * the headline write-amplification ratio (derived bytes vs. source bytes), all
 * measured live from the B2 `projects/` tree.
 */
export function ArchiveStats() {
  const { data, isLoading, error, refetch } = useProjectStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const amp = data?.write_amplification;
  const cards = [
    { title: "Projects", value: data?.project_count ?? 0, icon: Building2 },
    { title: "Source models", value: data?.model_count ?? 0, icon: Boxes },
    { title: "Derived artifacts", value: data?.artifact_count ?? 0, icon: FileStack },
    {
      title: "Write amplification",
      value: amp ? `${amp.ratio.toFixed(2)}×` : "0×",
      icon: ArrowUpRight,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card key={card.title} className={`card-hover animate-fade-in-up stagger-${i + 1}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 px-4 pb-2 pt-4">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-5">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
