import { SOURCE_DEFINITIONS } from "@/lib/vector/constants"
import { extractVocabularyFromContext } from "@/lib/vector/context"
import type { RuntimeContextPayload, VectorState } from "@/lib/vector/types"

const CAPABILITY_MAP = [
  "fetch_amplitude",
  "fetch_typeform",
  "read_release_notes_file",
  "fetch_itunes_lookup_metadata",
  "write_report_draft_primitive",
  "update_report_section_primitive",
  "get_evidence_for_claim",
  "complete_task",
  "render_blockkit_preview",
  "post_slack_message",
]

export function buildRuntimeContextPayload(state: VectorState): RuntimeContextPayload {
  const productContextContent =
    (state.snapshots.product_context?.data as { content?: string } | undefined)?.content ?? ""
  const vocabulary = extractVocabularyFromContext(productContextContent)

  const latestRun = state.runs[state.runs.length - 1]
  const statusSummary = latestRun
    ? `run ${latestRun.id} completed with ${latestRun.errorCount} adapter errors`
    : "no completed ingest run"

  return {
    sourceInventory: SOURCE_DEFINITIONS.map((source) => {
      const status = state.statusIndex[source.key]
      return {
        key: source.key,
        id: source.id,
        name: source.name,
        status: status.status,
        snapshotId: status.snapshotId,
        lastSuccessAt: status.lastSuccessAt,
      }
    }),
    capabilityMap: CAPABILITY_MAP,
    vocabulary,
    recentRunState: {
      runId: latestRun?.id ?? null,
      completedAt: latestRun?.completedAt ?? null,
      statusSummary,
    },
  }
}

export function buildPromptSnapshot(payload: RuntimeContextPayload): string {
  const sourceSummary = payload.sourceInventory
    .map(
      (source) =>
        `${source.name} (${source.status}${source.snapshotId ? `, snapshot=${source.snapshotId}` : ""})`
    )
    .join("; ")

  const vocabularyLine =
    payload.vocabulary.length > 0
      ? payload.vocabulary.join(", ")
      : "No product vocabulary extracted from context docs"

  return [
    "System: You are Vector, a product intelligence synthesis agent.",
    "",
    `Source inventory: ${sourceSummary}`,
    `Capability map: ${payload.capabilityMap.join(", ")}`,
    `Vocabulary: ${vocabularyLine}`,
    `Recent run state: ${payload.recentRunState.statusSummary}`,
    "",
    "Task: Produce the weekly decision brief with sections, hypotheses, recommendations, and evidence links.",
    "Completion contract: call complete_task with status success | partial | blocked and a concise summary.",
  ].join("\n")
}
