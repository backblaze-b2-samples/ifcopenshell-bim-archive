import type {
  Discipline,
  GeometryDetail,
  ProjectStatus,
} from "@ifcopenshell-bim-archive/shared";

// The pipeline's ordered stages — one source of truth for the timeline UI and
// the optimistic "running" projection in queries.ts. Mirrors the backend STAGES
// in services/api/app/service/archive_runner.py.
export const PIPELINE_STAGE_NAMES = ["Parse", "Extract Geometry", "Analyze"] as const;

// Finite option sets — the single source of truth for the create/edit selectors,
// the ingest discipline picker, and label rendering. Never free text.
export const DISCIPLINE_OPTIONS: { value: Discipline; label: string }[] = [
  { value: "architectural", label: "Architectural" },
  { value: "structural", label: "Structural" },
  { value: "mechanical", label: "Mechanical" },
  { value: "electrical", label: "Electrical" },
  { value: "plumbing", label: "Plumbing" },
  { value: "civil", label: "Civil" },
  { value: "coordination", label: "Coordination (all disciplines)" },
];

export const GEOMETRY_DETAIL_OPTIONS: {
  value: GeometryDetail;
  label: string;
  hint: string;
}[] = [
  { value: "coarse", label: "Coarse", hint: "Fastest, lowest mesh fidelity" },
  {
    value: "standard",
    label: "Standard",
    hint: "Balanced mesh detail — good for a first run",
  },
  { value: "fine", label: "Fine", hint: "Highest fidelity, slower to mesh" },
];

export function disciplineLabel(value: string): string {
  return DISCIPLINE_OPTIONS.find((d) => d.value === value)?.label ?? value;
}

export function geometryDetailLabel(value: string): string {
  return GEOMETRY_DETAIL_OPTIONS.find((g) => g.value === value)?.label ?? value;
}

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

export const STATUS_META: Record<
  ProjectStatus,
  { label: string; variant: BadgeVariant }
> = {
  draft: { label: "Draft", variant: "outline" },
  queued: { label: "Queued", variant: "secondary" },
  running: { label: "Running", variant: "secondary" },
  succeeded: { label: "Succeeded", variant: "default" },
  failed: { label: "Failed", variant: "destructive" },
};
