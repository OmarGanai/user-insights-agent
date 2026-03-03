import type {
  Evidence,
  Hypothesis,
  PipelineStep,
  Recommendation,
  ReportSection,
  Source,
  SourceStatus,
} from "@/lib/mock-data"

export type VectorSourceKey =
  | "amplitude"
  | "typeform"
  | "ios_release"
  | "product_context"
  | "company_context"

export type VectorSourceId =
  | "src-amplitude"
  | "src-typeform"
  | "src-ios"
  | "src-product-context"
  | "src-company-context"

export interface SourceDefinition {
  key: VectorSourceKey
  id: VectorSourceId
  name: string
  type: Source["type"]
}

export interface SourceStatusRecord {
  sourceKey: VectorSourceKey
  sourceId: VectorSourceId
  status: SourceStatus
  lastAttemptAt: string | null
  lastSuccessAt: string | null
  latestRunId: string | null
  snapshotId: string | null
  error: string | null
  caveat: string | null
}

export interface NormalizedSourceSnapshot<TData = Record<string, unknown>> {
  id: string
  sourceKey: VectorSourceKey
  sourceId: VectorSourceId
  runId: string
  capturedAt: string
  summary: string
  recordCount: number
  data: TData
}

export interface IngestRunRecord {
  id: string
  startedAt: string
  completedAt: string
  sourceKeys: VectorSourceKey[]
  statusBySource: Record<VectorSourceKey, SourceStatus>
  errorCount: number
}

export type CompletionSignalStatus = "success" | "partial" | "blocked"

export interface CompletionSignal {
  status: CompletionSignalStatus
  summary: string
  completedAt: string
}

export interface RuntimeContextPayload {
  sourceInventory: Array<{
    key: VectorSourceKey
    id: VectorSourceId
    name: string
    status: SourceStatus
    snapshotId: string | null
    lastSuccessAt: string | null
  }>
  capabilityMap: string[]
  vocabulary: string[]
  recentRunState: {
    runId: string | null
    completedAt: string | null
    statusSummary: string
  }
}

export interface EvidenceResolution {
  evidenceId: string
  sourceKey: VectorSourceKey
  sourceName: string
  snippet: string
  confidence: Evidence["confidence"]
  snapshotId: string | null
  runId: string | null
  traceStepId: string | null
}

export interface ReportRunMetadata {
  runId: string
  generatedAt: string
  completion: CompletionSignal
  runtimeContext: RuntimeContextPayload
  promptSnapshot: string
  traceId: string
  traceStepIds: string[]
}

export type PublishResultStatus = "success" | "failed"
export type PublishMode = "webhook" | "dry_run"

export interface PublishMetadata {
  attemptedAt: string
  destinationLabel: string
  status: PublishResultStatus
  mode: PublishMode
  error?: string
  httpStatus?: number
}

export interface ReportArtifact {
  id: string
  periodLabel: string
  sections: ReportSection[]
  hypotheses: Hypothesis[]
  recommendations: Recommendation[]
  evidenceMap: Record<string, EvidenceResolution>
  runMetadata: ReportRunMetadata
  updatedAt: string
  publishMetadata: PublishMetadata | null
  edits: Array<{
    sectionId: string
    editedAt: string
  }>
}

export interface PipelineTrace {
  id: string
  runId: string
  createdAt: string
  steps: PipelineStep[]
  promptSnapshot: string
}

export interface VectorState {
  schemaVersion: 1
  initializedAt: string
  updatedAt: string
  statusIndex: Record<VectorSourceKey, SourceStatusRecord>
  snapshots: Partial<Record<VectorSourceKey, NormalizedSourceSnapshot>>
  runs: IngestRunRecord[]
  artifact: ReportArtifact | null
  traces: Record<string, PipelineTrace>
  latestTraceId: string | null
}

export interface IngestOptions {
  sourceKey?: VectorSourceKey
  forceErrorSourceKey?: VectorSourceKey
}

export interface IngestResult {
  run: IngestRunRecord
  sourceInventory: Source[]
  statusIndex: Record<VectorSourceKey, SourceStatusRecord>
}

export interface SourceStatusResponse {
  sourceInventory: Source[]
  statusIndex: Record<VectorSourceKey, SourceStatusRecord>
  latestRun: IngestRunRecord | null
}

export interface SlackTextObject {
  type: "mrkdwn" | "plain_text"
  text: string
}

export type SlackBlock =
  | { type: "header"; text: SlackTextObject }
  | { type: "section"; text: SlackTextObject }
  | { type: "context"; elements: SlackTextObject[] }
  | { type: "divider" }

export interface SlackPayload {
  text: string
  blocks: SlackBlock[]
}
