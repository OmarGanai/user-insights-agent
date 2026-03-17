import { promises as fs } from "node:fs"
import path from "node:path"
import { SOURCE_DEFINITIONS } from "@/lib/vector/constants"
import { isoNow } from "@/lib/vector/time"
import type { SourceStatusRecord, VectorSourceKey, VectorState } from "@/lib/vector/types"

function vectorDataDir(): string {
  const override = process.env.VECTOR_DATA_DIR
  if (override && override.trim().length > 0) {
    return path.resolve(override)
  }
  return path.join(process.cwd(), ".vector-data")
}

function stateFilePath(): string {
  return path.join(vectorDataDir(), "state.json")
}

function createInitialStatusIndex(): Record<VectorSourceKey, SourceStatusRecord> {
  const statusIndex = {} as Record<VectorSourceKey, SourceStatusRecord>
  for (const source of SOURCE_DEFINITIONS) {
    statusIndex[source.key] = {
      sourceKey: source.key,
      sourceId: source.id,
      status: "stale",
      lastAttemptAt: null,
      lastSuccessAt: null,
      latestRunId: null,
      snapshotId: null,
      error: null,
      caveat: null,
    }
  }
  return statusIndex
}

export function createInitialVectorState(): VectorState {
  const now = isoNow()
  return {
    schemaVersion: 1,
    initializedAt: now,
    updatedAt: now,
    statusIndex: createInitialStatusIndex(),
    snapshots: {},
    runs: [],
    artifact: null,
    traces: {},
    latestTraceId: null,
  }
}

async function ensureStateFile(): Promise<void> {
  const filePath = stateFilePath()
  await fs.mkdir(path.dirname(filePath), { recursive: true })

  try {
    await fs.access(filePath)
  } catch {
    const initialState = createInitialVectorState()
    await fs.writeFile(filePath, JSON.stringify(initialState, null, 2), "utf8")
  }
}

let writeChain = Promise.resolve()

export async function readVectorState(): Promise<VectorState> {
  await ensureStateFile()
  const raw = await fs.readFile(stateFilePath(), "utf8")
  const parsed = JSON.parse(raw) as VectorState
  return parsed
}

export async function writeVectorState(nextState: VectorState): Promise<void> {
  const filePath = stateFilePath()
  const payload = JSON.stringify(nextState, null, 2)

  writeChain = writeChain.then(async () => {
    await fs.mkdir(path.dirname(filePath), { recursive: true })
    const tempFile = `${filePath}.tmp`
    await fs.writeFile(tempFile, payload, "utf8")
    await fs.rename(tempFile, filePath)
  })

  await writeChain
}

export async function updateVectorState(
  mutate: (state: VectorState) => void | Promise<void>
): Promise<VectorState> {
  const state = await readVectorState()
  await mutate(state)
  state.updatedAt = isoNow()
  await writeVectorState(state)
  return state
}

export async function resetVectorStateForTests(): Promise<void> {
  const initial = createInitialVectorState()
  await writeVectorState(initial)
}
