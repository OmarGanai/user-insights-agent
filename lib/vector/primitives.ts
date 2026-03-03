import { buildRuntimeContextPayload, buildPromptSnapshot } from "@/lib/vector/runtime"
import { readVectorState, writeVectorState } from "@/lib/vector/store"
import { synthesizeReportDraft } from "@/lib/vector/synthesis"
import { isoNow } from "@/lib/vector/time"
import type {
  EvidenceResolution,
  PipelineTrace,
  PublishMetadata,
  ReportArtifact,
} from "@/lib/vector/types"

export async function writeReportDraftPrimitive(): Promise<{
  artifact: ReportArtifact
  trace: PipelineTrace
}> {
  const state = await readVectorState()
  const runtimeContext = buildRuntimeContextPayload(state)
  const promptSnapshot = buildPromptSnapshot(runtimeContext)

  const synthesis = synthesizeReportDraft(state, runtimeContext)
  const traceId = `trace-${Date.now()}`
  const runId = state.runs[state.runs.length - 1]?.id ?? `run-synthesis-${Date.now()}`

  const trace: PipelineTrace = {
    id: traceId,
    runId,
    createdAt: isoNow(),
    steps: synthesis.traceSteps,
    promptSnapshot,
  }

  const artifact: ReportArtifact = {
    id: state.artifact?.id ?? `artifact-${runId}`,
    periodLabel: synthesis.periodLabel,
    sections: synthesis.sections,
    hypotheses: synthesis.hypotheses,
    recommendations: synthesis.recommendations,
    evidenceMap: synthesis.evidenceMap,
    runMetadata: {
      runId,
      generatedAt: isoNow(),
      completion: synthesis.completion,
      runtimeContext,
      promptSnapshot,
      traceId,
      traceStepIds: synthesis.traceSteps.map((step) => step.id),
    },
    publishMetadata: state.artifact?.publishMetadata ?? null,
    edits: [],
    updatedAt: isoNow(),
  }

  state.artifact = artifact
  state.traces[traceId] = trace
  state.latestTraceId = traceId
  state.updatedAt = isoNow()

  await writeVectorState(state)

  return { artifact, trace }
}

export async function getReportArtifactPrimitive(): Promise<ReportArtifact | null> {
  const state = await readVectorState()
  return state.artifact
}

export async function updateReportSectionPrimitive(
  sectionId: string,
  content: string
): Promise<ReportArtifact> {
  const state = await readVectorState()
  const artifact = state.artifact

  if (!artifact) {
    throw new Error("Report artifact does not exist. Generate a draft first.")
  }

  const sectionExists = artifact.sections.some((section) => section.id === sectionId)
  if (!sectionExists) {
    throw new Error(`Unknown section id: ${sectionId}`)
  }

  artifact.sections = artifact.sections.map((section) =>
    section.id === sectionId ? { ...section, content } : section
  )
  artifact.updatedAt = isoNow()
  artifact.edits = [...artifact.edits, { sectionId, editedAt: isoNow() }]

  state.artifact = artifact
  state.updatedAt = isoNow()
  await writeVectorState(state)

  return artifact
}

export async function savePublishMetadataPrimitive(
  metadata: PublishMetadata
): Promise<ReportArtifact> {
  const state = await readVectorState()
  const artifact = state.artifact

  if (!artifact) {
    throw new Error("Report artifact does not exist. Generate a draft first.")
  }

  artifact.publishMetadata = metadata
  artifact.updatedAt = isoNow()
  state.artifact = artifact
  state.updatedAt = isoNow()
  await writeVectorState(state)
  return artifact
}

export async function getEvidenceForClaimPrimitive(
  evidenceId: string
): Promise<EvidenceResolution> {
  const state = await readVectorState()
  const artifact = state.artifact

  if (!artifact) {
    throw new Error("Report artifact does not exist. Generate a draft first.")
  }

  const evidence = artifact.evidenceMap[evidenceId]
  if (!evidence) {
    throw new Error(`Evidence not found for claim id: ${evidenceId}`)
  }

  return evidence
}

export async function getLatestTracePrimitive(): Promise<PipelineTrace | null> {
  const state = await readVectorState()
  if (!state.latestTraceId) {
    return null
  }

  return state.traces[state.latestTraceId] ?? null
}
