import { QueryClient } from "@tanstack/react-query";
import { beforeEach, describe, expect, it } from "vitest";
import { dropDeletedFileFromCache, markProjectRunning, qk } from "@/lib/queries";
import type { FileMetadata, Project } from "@ifcopenshell-bim-archive/shared";

function file(key: string): FileMetadata {
  return {
    key,
    filename: key.split("/").pop() ?? key,
    folder: "uploads/",
    size_bytes: 10,
    size_human: "10 B",
    content_type: "text/plain",
    uploaded_at: "2026-07-28T00:00:00Z",
    url: null,
  };
}

describe("dropDeletedFileFromCache", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = new QueryClient();
  });

  it("removes the deleted row from the default list", () => {
    qc.setQueryData(qk.files(), [file("uploads/a.txt"), file("uploads/b.txt")]);

    dropDeletedFileFromCache(qc, "uploads/a.txt");

    expect(qc.getQueryData<FileMetadata[]>(qk.files())).toEqual([
      file("uploads/b.txt"),
    ]);
  });

  it("removes it from every cached prefix/limit variant", () => {
    qc.setQueryData(qk.files(), [file("uploads/a.txt")]);
    qc.setQueryData(qk.files("uploads/", 100), [file("uploads/a.txt")]);
    qc.setQueryData(qk.files("", 25), [file("uploads/a.txt")]);

    dropDeletedFileFromCache(qc, "uploads/a.txt");

    expect(qc.getQueryData<FileMetadata[]>(qk.files())).toEqual([]);
    expect(qc.getQueryData<FileMetadata[]>(qk.files("uploads/", 100))).toEqual(
      [],
    );
    expect(qc.getQueryData<FileMetadata[]>(qk.files("", 25))).toEqual([]);
  });

  it("evicts the deleted key's presigned URL and detail so Preview can't 404", () => {
    qc.setQueryData(qk.preview("uploads/a.txt"), { url: "https://signed" });
    qc.setQueryData(qk.detail("uploads/a.txt"), { md5: "abc" });

    dropDeletedFileFromCache(qc, "uploads/a.txt");

    expect(qc.getQueryData(qk.preview("uploads/a.txt"))).toBeUndefined();
    expect(qc.getQueryData(qk.detail("uploads/a.txt"))).toBeUndefined();
  });

  it("leaves other files' cached previews alone", () => {
    qc.setQueryData(qk.preview("uploads/b.txt"), { url: "https://signed-b" });

    dropDeletedFileFromCache(qc, "uploads/a.txt");

    expect(qc.getQueryData(qk.preview("uploads/b.txt"))).toEqual({
      url: "https://signed-b",
    });
  });

  it("does not touch stats or activity caches", () => {
    qc.setQueryData(qk.stats(), { total_files: 2 });
    qc.setQueryData(qk.uploadActivity(7), [{ date: "2026-07-28", uploads: 2 }]);

    dropDeletedFileFromCache(qc, "uploads/a.txt");

    expect(qc.getQueryData(qk.stats())).toEqual({ total_files: 2 });
    expect(qc.getQueryData(qk.uploadActivity(7))).toHaveLength(1);
  });

  it("is a no-op for an unseeded cache", () => {
    expect(() =>
      dropDeletedFileFromCache(qc, "uploads/missing.txt"),
    ).not.toThrow();
    expect(qc.getQueryData(qk.files())).toBeUndefined();
  });
});

function project(overrides: Partial<Project> = {}): Project {
  return {
    slug: "riverside",
    name: "Riverside Hospital",
    discipline: "coordination",
    geometry_detail: "standard",
    status: "draft",
    created_at: "2026-08-13T00:00:00Z",
    updated_at: "2026-08-13T00:00:00Z",
    last_run_at: null,
    models: [],
    pipeline: [],
    stats: null,
    write_amplification: null,
    error: null,
    ...overrides,
  };
}

describe("markProjectRunning", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = new QueryClient();
  });

  it("flips the cached project to running with running stages", () => {
    qc.setQueryData(qk.project("riverside"), project({ error: "old failure" }));

    const previous = markProjectRunning(qc, "riverside");

    expect(previous?.status).toBe("draft");
    const now = qc.getQueryData<Project>(qk.project("riverside"))!;
    expect(now.status).toBe("running");
    expect(now.error).toBeNull();
    expect(now.pipeline.map((s) => s.name)).toEqual([
      "Parse",
      "Extract Geometry",
      "Analyze",
    ]);
    expect(now.pipeline.every((s) => s.status === "running")).toBe(true);
  });

  it("is a no-op when the project isn't cached", () => {
    expect(markProjectRunning(qc, "missing")).toBeUndefined();
    expect(qc.getQueryData(qk.project("missing"))).toBeUndefined();
  });
});
