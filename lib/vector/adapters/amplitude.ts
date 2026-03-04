import { MOCK_SOURCES } from "@/lib/mock-data"
import { sourceIdFromKey } from "@/lib/vector/constants"
import { isoNow } from "@/lib/vector/time"
import type { NormalizedSourceSnapshot } from "@/lib/vector/types"

export interface AmplitudeChartSnapshot {
  id: string
  name: string
  chartType: string
  source: "live" | "seeded"
  dataPoints: number
  url?: string
  lastUpdated?: string
}

export interface FetchAmplitudeOptions {
  runId: string
  fetchImpl?: typeof fetch
  forceError?: boolean
}

export interface AdapterResult<TData> {
  snapshot: NormalizedSourceSnapshot<TData>
  caveat?: string | null
}

const DEFAULT_AMPLITUDE_MAX_ATTEMPTS = 3
const DEFAULT_AMPLITUDE_RETRY_BASE_DELAY_MS = 1000
const DEFAULT_AMPLITUDE_INTER_REQUEST_DELAY_MS = 350

class AmplitudeApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly retryAfterMs: number | null = null
  ) {
    super(message)
    this.name = "AmplitudeApiError"
  }
}

function readPositiveIntEnv(name: string, fallback: number): number {
  const raw = process.env[name]
  if (!raw) {
    return fallback
  }

  const parsed = Number.parseInt(raw, 10)
  if (!Number.isFinite(parsed) || parsed < 0) {
    return fallback
  }

  return parsed
}

function parseRetryAfterMs(value: string | null): number | null {
  if (!value) {
    return null
  }

  const asSeconds = Number.parseInt(value, 10)
  if (Number.isFinite(asSeconds) && asSeconds >= 0) {
    return asSeconds * 1000
  }

  const asDate = Date.parse(value)
  if (Number.isFinite(asDate)) {
    return Math.max(0, asDate - Date.now())
  }

  return null
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function countDataPoints(value: unknown): number {
  if (Array.isArray(value)) {
    return value.reduce((acc, item) => acc + countDataPoints(item), 0)
  }

  if (value && typeof value === "object") {
    return Object.values(value).reduce((acc, item) => acc + countDataPoints(item), 0)
  }

  return typeof value === "number" ? 1 : 0
}

function fallbackCharts(): AmplitudeChartSnapshot[] {
  const mockAmplitude = MOCK_SOURCES.find((source) => source.type === "amplitude")
  if (!mockAmplitude?.charts) {
    return []
  }

  return mockAmplitude.charts.map((chart) => ({
    id: chart.id,
    name: chart.name,
    chartType: chart.chartType,
    source: "seeded" as const,
    dataPoints: 50,
    url: chart.url,
    lastUpdated: chart.lastUpdated,
  }))
}

async function fetchChartFromAmplitude(
  chartId: string,
  fetchImpl: typeof fetch,
  authHeader: string
): Promise<AmplitudeChartSnapshot> {
  const response = await fetchImpl(`https://amplitude.com/api/3/chart/${chartId}/query`, {
    method: "GET",
    headers: {
      Authorization: authHeader,
      Accept: "application/json",
    },
    cache: "no-store",
  })

  if (!response.ok) {
    const body = await response.text()
    throw new AmplitudeApiError(
      `Amplitude chart ${chartId} failed (${response.status}): ${body || "unknown"}`,
      response.status,
      parseRetryAfterMs(response.headers.get("retry-after"))
    )
  }

  const payload = (await response.json()) as Record<string, unknown>
  const chart = (payload.chart as Record<string, unknown> | undefined) ?? {}
  const series = payload.series ?? payload.data ?? payload

  return {
    id: chartId,
    name: String(chart.name ?? chart.title ?? chartId),
    chartType: String(chart.chart_type ?? chart.type ?? "unknown"),
    source: "live",
    dataPoints: countDataPoints(series),
    url: typeof chart.url === "string" ? chart.url : undefined,
    lastUpdated: isoNow(),
  }
}

function isRetryableAmplitudeStatus(status: number): boolean {
  return status === 429 || status >= 500
}

function retryDelayMs(error: AmplitudeApiError, attempt: number, baseDelayMs: number): number {
  if (error.retryAfterMs !== null) {
    return error.retryAfterMs
  }

  const exponential = baseDelayMs * Math.max(1, 2 ** (attempt - 1))
  const jitter = Math.floor(Math.random() * 200)
  return exponential + jitter
}

async function fetchChartWithRetry(
  chartId: string,
  fetchImpl: typeof fetch,
  authHeader: string,
  maxAttempts: number,
  baseDelayMs: number
): Promise<AmplitudeChartSnapshot> {
  let lastError: unknown = null

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await fetchChartFromAmplitude(chartId, fetchImpl, authHeader)
    } catch (error) {
      lastError = error
      if (!(error instanceof AmplitudeApiError)) {
        throw error
      }

      if (!isRetryableAmplitudeStatus(error.status) || attempt === maxAttempts) {
        throw error
      }

      await sleep(retryDelayMs(error, attempt, baseDelayMs))
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error(`Amplitude chart ${chartId} failed with unknown retry error.`)
}

/**
 * fetch_amplitude adapter
 *
 * Auth handling:
 * - Uses HTTP Basic auth with `AMPLITUDE_API_KEY:AMPLITUDE_SECRET_KEY` encoded as base64.
 * - Requires `AMPLITUDE_CHART_IDS` (comma-separated) for live chart selection.
 *
 * Payload handling:
 * - Reads each chart query payload from `/api/3/chart/{chartId}/query`.
 * - Normalizes chart metadata + point counts into a compact snapshot consumed by synthesis.
 * - Falls back to seeded chart snapshots when credentials are not configured.
 */
export async function fetchAmplitude(
  options: FetchAmplitudeOptions
): Promise<AdapterResult<{ charts: AmplitudeChartSnapshot[] }>> {
  const { runId, fetchImpl = fetch, forceError = false } = options

  if (forceError) {
    throw new Error("Forced amplitude adapter failure")
  }

  const apiKey = process.env.AMPLITUDE_API_KEY
  const secret = process.env.AMPLITUDE_SECRET_KEY
  const chartIds = (process.env.AMPLITUDE_CHART_IDS ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
  const maxAttempts = Math.max(
    1,
    readPositiveIntEnv("AMPLITUDE_MAX_ATTEMPTS", DEFAULT_AMPLITUDE_MAX_ATTEMPTS)
  )
  const baseDelayMs = readPositiveIntEnv(
    "AMPLITUDE_RETRY_BASE_DELAY_MS",
    DEFAULT_AMPLITUDE_RETRY_BASE_DELAY_MS
  )
  const interRequestDelayMs = readPositiveIntEnv(
    "AMPLITUDE_INTER_REQUEST_DELAY_MS",
    DEFAULT_AMPLITUDE_INTER_REQUEST_DELAY_MS
  )

  let charts: AmplitudeChartSnapshot[] = []
  let caveat: string | null = null

  if (!apiKey || !secret || chartIds.length === 0) {
    charts = fallbackCharts()
    caveat = "Using seeded Amplitude data. Configure AMPLITUDE_API_KEY, AMPLITUDE_SECRET_KEY, and AMPLITUDE_CHART_IDS for live ingest."
  } else {
    const authHeader = `Basic ${Buffer.from(`${apiKey}:${secret}`).toString("base64")}`
    const failedChartIds: string[] = []
    const failureReasons: string[] = []

    for (let index = 0; index < chartIds.length; index += 1) {
      const chartId = chartIds[index]

      try {
        const chart = await fetchChartWithRetry(
          chartId,
          fetchImpl,
          authHeader,
          maxAttempts,
          baseDelayMs
        )
        charts.push(chart)
      } catch (error) {
        failedChartIds.push(chartId)
        if (error instanceof Error) {
          failureReasons.push(error.message)
        }
      }

      if (index < chartIds.length - 1 && interRequestDelayMs > 0) {
        await sleep(interRequestDelayMs)
      }
    }

    if (charts.length === 0) {
      const reason = failureReasons[0] ?? "All chart queries failed."
      throw new Error(
        `Amplitude ingest failed for all charts (${chartIds.length} requested). ${reason}`
      )
    }

    if (failedChartIds.length > 0) {
      caveat =
        `Partial Amplitude ingest (${charts.length}/${chartIds.length} charts). ` +
        `Failed chart ids: ${failedChartIds.join(", ")}.`
    }
  }

  const capturedAt = isoNow()
  const snapshot: NormalizedSourceSnapshot<{ charts: AmplitudeChartSnapshot[] }> = {
    id: `${sourceIdFromKey("amplitude")}-${runId}`,
    sourceKey: "amplitude",
    sourceId: sourceIdFromKey("amplitude"),
    runId,
    capturedAt,
    summary: `${charts.length} charts normalized from Amplitude`,
    recordCount: charts.reduce((acc, chart) => acc + chart.dataPoints, 0),
    data: { charts },
  }

  return { snapshot, caveat }
}
