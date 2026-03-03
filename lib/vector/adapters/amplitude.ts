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
    throw new Error(`Amplitude chart ${chartId} failed (${response.status}): ${body || "unknown"}`)
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

  let charts: AmplitudeChartSnapshot[]
  let caveat: string | null = null

  if (!apiKey || !secret || chartIds.length === 0) {
    charts = fallbackCharts()
    caveat = "Using seeded Amplitude data. Configure AMPLITUDE_API_KEY, AMPLITUDE_SECRET_KEY, and AMPLITUDE_CHART_IDS for live ingest."
  } else {
    const authHeader = `Basic ${Buffer.from(`${apiKey}:${secret}`).toString("base64")}`
    charts = await Promise.all(
      chartIds.map((chartId) => fetchChartFromAmplitude(chartId, fetchImpl, authHeader))
    )
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
