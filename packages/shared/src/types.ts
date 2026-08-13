export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- BIM archive: project + pipeline domain -------------------------------

export type ProjectStatus =
  | "draft"
  | "queued"
  | "running"
  | "succeeded"
  | "failed";

export type Discipline =
  | "architectural"
  | "structural"
  | "mechanical"
  | "electrical"
  | "plumbing"
  | "civil"
  | "coordination";

export type GeometryDetail = "coarse" | "standard" | "fine";

export interface ProjectCreate {
  name: string;
  discipline: Discipline;
  geometry_detail: GeometryDetail;
}

export interface ProjectUpdate {
  name?: string;
  discipline?: Discipline;
  geometry_detail?: GeometryDetail;
}

export interface ModelEntry {
  key: string;
  filename: string;
  discipline: Discipline;
  size_bytes: number;
  size_human: string;
  uploaded_at: string | null;
}

export interface PipelineStage {
  name: string;
  status: ProjectStatus;
  detail: string;
}

export interface BimStats {
  model_count: number;
  element_count: number;
  space_count: number;
  storey_count: number;
  mesh_count: number;
  type_counts: Record<string, number>;
  discipline_counts: Record<string, number>;
  clash_candidate_count: number;
}

export interface WriteAmplification {
  source_bytes: number;
  artifact_bytes: number;
  total_bytes: number;
  source_human: string;
  artifact_human: string;
  total_human: string;
  ratio: number;
}

export interface ArtifactEntry {
  key: string;
  filename: string;
  kind: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string | null;
}

export interface Project {
  slug: string;
  name: string;
  discipline: Discipline;
  geometry_detail: GeometryDetail;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  last_run_at: string | null;
  models: ModelEntry[];
  pipeline: PipelineStage[];
  stats: BimStats | null;
  write_amplification: WriteAmplification | null;
  error: string | null;
}

export interface ProjectStats {
  project_count: number;
  model_count: number;
  artifact_count: number;
  write_amplification: WriteAmplification;
}

export interface ServerCapabilities {
  engine: string;
  engine_version: string;
  device: string;
  disciplines: string[];
  geometry_details: string[];
  accepted_extensions: string[];
}

export interface IngestPresignRequest {
  filename: string;
  discipline: Discipline;
  content_type: string;
  size_bytes: number;
}
