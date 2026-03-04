import { SOURCE_DEFINITIONS, sourceDefinitionForKey } from "@/lib/vector/constants"
import { loadContextSnapshots } from "@/lib/vector/context"
import { fetchAmplitude } from "@/lib/vector/adapters/amplitude"
import { fetchTypeform } from "@/lib/vector/adapters/typeform"
import { fetchIosRelease } from "@/lib/vector/adapters/ios"
import { readVectorState, writeVectorState } from "@/lib/vector/store"
import { isoNow, toRelativeTime } from "@/lib/vector/time"
import type {
  IngestOptions,
  IngestResult,
  IngestRunRecord,
  SourceStatusResponse,
  VectorSourceKey,
  VectorState,
} from "@/lib/vector/types"
import type { Source, SourceStatus } from "@/lib/mock-data"

function buildRunId(): string {
  return `run-${Date.now()}`
}

function sourceStatusSummary(statusBySource: Record<VectorSourceKey, SourceStatus>): string {
  const counts = Object.values(statusBySource).reduce(
    (acc, status) => {
      acc[status] += 1
      return acc
    },
    { synced: 0, stale: 0, syncing: 0, error: 0 }
  )

  return `${counts.synced} synced, ${counts.error} errors`
}

export function buildSourceInventory(state: VectorState): Source[] {
  return SOURCE_DEFINITIONS.map((definition) => {
    const status = state.statusIndex[definition.key]
    const snapshot = state.snapshots[definition.key]

    const base: Source = {
      id: definition.id,
      name: definition.name,
      type: definition.type,
      status: status.status,
      lastSync: toRelativeTime(status.lastSuccessAt),
      recordCount: snapshot?.recordCount ?? 0,
      error: status.error ?? undefined,
      notice: status.caveat ?? undefined,
    }

    if (definition.key === "amplitude") {
      const chartData = snapshot?.data as { charts?: Source["charts"] } | undefined
      base.charts = chartData?.charts
    }

    if (definition.key === "typeform") {
      const typeformData = snapshot?.data as { responseCount?: number } | undefined
      base.responseCount = typeformData?.responseCount ?? snapshot?.recordCount ?? 0
    }

    if (definition.key === "ios_release") {
      const iosData = snapshot?.data as
        | { latestVersion?: string; latestReleaseDate?: string }
        | undefined
      base.latestRelease = iosData?.latestVersion
      base.latestReleaseDate = iosData?.latestReleaseDate
    }

    return base
  })
}

async function runSingleSource(
  sourceKey: VectorSourceKey,
  runId: string,
  forceErrorSourceKey?: VectorSourceKey
) {
  if (sourceKey === "amplitude") {
    return fetchAmplitude({ runId, forceError: forceErrorSourceKey === "amplitude" })
  }

  if (sourceKey === "typeform") {
    return fetchTypeform({ runId, forceError: forceErrorSourceKey === "typeform" })
  }

  if (sourceKey === "ios_release") {
    return fetchIosRelease({ runId, forceError: forceErrorSourceKey === "ios_release" })
  }

  const contextSnapshots = await loadContextSnapshots(runId)
  const snapshot = contextSnapshots.find((item) => item.sourceKey === sourceKey)
  if (!snapshot) {
    throw new Error(`Context snapshot missing for source ${sourceKey}`)
  }

  return { snapshot, caveat: null }
}

export async function refreshSources(options: IngestOptions = {}): Promise<IngestResult> {
  const startedAt = isoNow()
  const runId = buildRunId()
  const sourceKeys = options.sourceKey
    ? [options.sourceKey]
    : SOURCE_DEFINITIONS.map((definition) => definition.key)

  const state = await readVectorState()

  for (const sourceKey of sourceKeys) {
    const status = state.statusIndex[sourceKey]
    state.statusIndex[sourceKey] = {
      ...status,
      status: "syncing",
      lastAttemptAt: startedAt,
      error: null,
    }
  }

  await writeVectorState({ ...state, updatedAt: isoNow() })

  const statusBySource = {} as Record<VectorSourceKey, SourceStatus>

  for (const definition of SOURCE_DEFINITIONS) {
    statusBySource[definition.key] = state.statusIndex[definition.key].status
  }

  for (const sourceKey of sourceKeys) {
    try {
      const { snapshot, caveat } = await runSingleSource(sourceKey, runId, options.forceErrorSourceKey)
      state.snapshots[sourceKey] = snapshot
      state.statusIndex[sourceKey] = {
        ...state.statusIndex[sourceKey],
        status: "synced",
        lastSuccessAt: snapshot.capturedAt,
        latestRunId: runId,
        snapshotId: snapshot.id,
        error: null,
        caveat: caveat ?? null,
      }
      statusBySource[sourceKey] = "synced"
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown adapter failure"
      state.statusIndex[sourceKey] = {
        ...state.statusIndex[sourceKey],
        status: "error",
        latestRunId: runId,
        error: message,
        caveat: null,
      }
      statusBySource[sourceKey] = "error"
    }
  }

  const run: IngestRunRecord = {
    id: runId,
    startedAt,
    completedAt: isoNow(),
    sourceKeys,
    statusBySource,
    errorCount: Object.values(statusBySource).filter((status) => status === "error").length,
  }

  state.runs.push(run)
  state.runs = state.runs.slice(-50)
  state.updatedAt = isoNow()

  await writeVectorState(state)

  return {
    run,
    sourceInventory: buildSourceInventory(state),
    statusIndex: state.statusIndex,
  }
}

export async function getSourceStatus(): Promise<SourceStatusResponse> {
  const state = await readVectorState()
  return {
    sourceInventory: buildSourceInventory(state),
    statusIndex: state.statusIndex,
    latestRun: state.runs[state.runs.length - 1] ?? null,
  }
}

export async function ensureInitialIngest(): Promise<SourceStatusResponse> {
  const state = await readVectorState()

  if (state.runs.length === 0) {
    await refreshSources()
  }

  const refreshedState = await readVectorState()
  return {
    sourceInventory: buildSourceInventory(refreshedState),
    statusIndex: refreshedState.statusIndex,
    latestRun: refreshedState.runs[refreshedState.runs.length - 1] ?? null,
  }
}

export function buildRecentRunSummary(state: VectorState): string {
  const latestRun = state.runs[state.runs.length - 1]
  if (!latestRun) {
    return "No ingest run completed yet"
  }

  return `Latest run ${latestRun.id}: ${sourceStatusSummary(latestRun.statusBySource)}`
}

export function sourceLabelFromKey(sourceKey: VectorSourceKey): string {
  return sourceDefinitionForKey(sourceKey).name
}
