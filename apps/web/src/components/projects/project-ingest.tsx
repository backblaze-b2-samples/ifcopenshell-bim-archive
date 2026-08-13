"use client";

import { useRef, useState } from "react";
import { FileUp, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useIngestModel, useIngestSamples } from "@/lib/queries";
import { DISCIPLINE_OPTIONS } from "@/lib/bim";
import type { Discipline } from "@ifcopenshell-bim-archive/shared";

export function ProjectIngest({ slug }: { slug: string }) {
  const ingestSamples = useIngestSamples(slug);
  const ingestModel = useIngestModel(slug);
  const [discipline, setDiscipline] = useState<Discipline>("architectural");
  const fileRef = useRef<HTMLInputElement>(null);

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".ifc")) {
      toast.error("Only .ifc models can be ingested");
      return;
    }
    try {
      await ingestModel.mutateAsync({ file, discipline });
      toast.success(`Ingested ${file.name}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const loadSamples = async () => {
    try {
      await ingestSamples.mutateAsync();
      toast.success("Loaded synthetic sample models (architectural + structural)");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load samples");
    }
  };

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Ingest IFC models</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-col gap-2 rounded-md border border-dashed border-border p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium">Load sample models</p>
            <p className="text-xs text-muted-foreground">
              Author two tiny, license-clean synthetic models server-side — zero
              setup for a first run.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={loadSamples}
            disabled={ingestSamples.isPending}
          >
            <Sparkles className="h-3.5 w-3.5" />
            {ingestSamples.isPending ? "Loading..." : "Load samples"}
          </Button>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              Bring your own IFC — discipline
            </p>
            <Select
              value={discipline}
              onValueChange={(v) => setDiscipline(v as Discipline)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DISCIPLINE_OPTIONS.map((d) => (
                  <SelectItem key={d.value} value={d.value}>
                    {d.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".ifc"
            className="hidden"
            onChange={(e) => onFile(e.target.files?.[0])}
          />
          <Button
            variant="outline"
            onClick={() => fileRef.current?.click()}
            disabled={ingestModel.isPending}
          >
            <FileUp className="h-4 w-4" />
            {ingestModel.isPending ? "Uploading..." : "Choose .ifc"}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Models upload directly to B2 under{" "}
          <code>projects/{slug}/models/&lt;discipline&gt;/</code>.
        </p>
      </CardContent>
    </Card>
  );
}
