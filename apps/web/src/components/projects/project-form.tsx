"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCreateProject, useUpdateProject } from "@/lib/queries";
import { DISCIPLINE_OPTIONS, GEOMETRY_DETAIL_OPTIONS } from "@/lib/bim";
import type { Discipline, GeometryDetail, Project } from "@ifcopenshell-bim-archive/shared";

const DISCIPLINE_VALUES = DISCIPLINE_OPTIONS.map((d) => d.value) as [
  Discipline,
  ...Discipline[],
];
const DETAIL_VALUES = GEOMETRY_DETAIL_OPTIONS.map((g) => g.value) as [
  GeometryDetail,
  ...GeometryDetail[],
];

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Name is required")
    .max(120, "Name must be 120 characters or fewer"),
  discipline: z.enum(DISCIPLINE_VALUES),
  geometry_detail: z.enum(DETAIL_VALUES),
});

type FormValues = z.infer<typeof schema>;

interface ProjectFormProps {
  /** Edit an existing project when provided; otherwise create a new one. */
  project?: Project;
  onSuccess?: (project: Project) => void;
  onCancel?: () => void;
}

export function ProjectForm({ project, onSuccess, onCancel }: ProjectFormProps) {
  const isEdit = !!project;
  const createMutation = useCreateProject();
  const updateMutation = useUpdateProject(project?.slug ?? "");
  const mutation = isEdit ? updateMutation : createMutation;

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    // Create opens with safe defaults; edit opens pre-filled from the project.
    defaultValues: {
      name: project?.name ?? "",
      discipline: project?.discipline ?? "coordination",
      geometry_detail: project?.geometry_detail ?? "standard",
    },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      const result = isEdit
        ? await updateMutation.mutateAsync(values)
        : await createMutation.mutateAsync(values);
      toast.success(isEdit ? "Project updated" : "Project created");
      onSuccess?.(result);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Could not save the project"
      );
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Project name</FormLabel>
              <FormControl>
                <Input placeholder="Riverside Community Hospital" {...field} />
              </FormControl>
              {!isEdit && (
                <FormDescription>
                  One building or coordination effort. You can rename it later.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="discipline"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Primary discipline</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {DISCIPLINE_OPTIONS.map((d) => (
                    <SelectItem key={d.value} value={d.value}>
                      {d.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!isEdit && (
                <FormDescription>
                  Defaults to Coordination (all disciplines). Each ingested model
                  gets its own discipline at upload time.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="geometry_detail"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Geometry detail</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {GEOMETRY_DETAIL_OPTIONS.map((g) => (
                    <SelectItem key={g.value} value={g.value}>
                      {g.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!isEdit && (
                <FormDescription>
                  Standard is a balanced mesh detail — good for a first run.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex items-center justify-end gap-2">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending
              ? "Saving..."
              : isEdit
                ? "Save changes"
                : "Create project"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
