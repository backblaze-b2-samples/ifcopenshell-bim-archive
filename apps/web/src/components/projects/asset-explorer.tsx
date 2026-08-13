"use client";

import { useState } from "react";
import { Download, FolderTree } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Badge } from "@/components/ui/badge";
import { useProjectArtifacts } from "@/lib/queries";
import { getArtifactDownloadUrl } from "@/lib/api-client";
import type { ArtifactEntry } from "@ifcopenshell-bim-archive/shared";

const KIND_ORDER = ["model", "metadata", "geometry", "analysis", "manifest"];

export function AssetExplorer({ slug }: { slug: string }) {
  const { data: artifacts, isLoading, error, refetch } = useProjectArtifacts(slug);
  const [pending, setPending] = useState<string | null>(null);

  const download = async (entry: ArtifactEntry) => {
    setPending(entry.key);
    try {
      const { url } = await getArtifactDownloadUrl(slug, entry.key);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not sign URL");
    } finally {
      setPending(null);
    }
  };

  const grouped = (artifacts ?? []).reduce<Record<string, ArtifactEntry[]>>(
    (acc, a) => {
      (acc[a.kind] ??= []).push(a);
      return acc;
    },
    {}
  );
  const kinds = Object.keys(grouped).sort(
    (a, b) => KIND_ORDER.indexOf(a) - KIND_ORDER.indexOf(b)
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">
          Project assets{" "}
          <span className="font-normal text-muted-foreground">
            (projects/{slug}/)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : (artifacts?.length ?? 0) === 0 ? (
          <EmptyState
            icon={FolderTree}
            title="No assets yet"
            description="Ingest a model and run the pipeline — the source IFC and every derived artifact will be listed here."
          />
        ) : (
          <div className="space-y-4">
            {kinds.map((kind) => (
              <div key={kind}>
                <div className="mb-1.5 flex items-center gap-2">
                  <Badge variant="outline" className="capitalize">
                    {kind}
                  </Badge>
                </div>
                <div className="divide-y divide-border rounded-md border border-border">
                  {grouped[kind].map((a) => (
                    <div
                      key={a.key}
                      className="flex items-center justify-between gap-3 px-3 py-2"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm">{a.filename}</p>
                        <p className="truncate font-mono text-xs text-muted-foreground">
                          {a.key}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-3">
                        <span className="font-mono text-xs tabular-nums text-muted-foreground">
                          {a.size_human}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => download(a)}
                          disabled={pending === a.key}
                        >
                          <Download className="h-3.5 w-3.5" />
                          <span className="sr-only">Download {a.filename}</span>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
