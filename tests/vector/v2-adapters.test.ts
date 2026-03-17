import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import { promises as fs } from "node:fs"
import path from "node:path"
import { fetchAmplitude } from "@/lib/vector/adapters/amplitude"
import { fetchTypeform } from "@/lib/vector/adapters/typeform"
import { fetchIosRelease } from "@/lib/vector/adapters/ios"
import { refreshSources } from "@/lib/vector/ingest"
import { resetVectorStateForTests } from "@/lib/vector/store"

const TEST_DIR = path.join(process.cwd(), ".tmp-vector-tests", "v2")

async function resetEnvAndState() {
  process.env.VECTOR_DATA_DIR = TEST_DIR
  delete process.env.AMPLITUDE_API_KEY
  delete process.env.AMPLITUDE_SECRET_KEY
  delete process.env.AMPLITUDE_CHART_IDS
  delete process.env.AMPLITUDE_MAX_ATTEMPTS
  delete process.env.AMPLITUDE_RETRY_BASE_DELAY_MS
  delete process.env.AMPLITUDE_INTER_REQUEST_DELAY_MS
  delete process.env.TYPEFORM_API_KEY
  delete process.env.TYPEFORM_FORM_ID
  delete process.env.IOS_APP_ID
  await fs.rm(TEST_DIR, { recursive: true, force: true })
  await resetVectorStateForTests()
}

describe("V2 adapters and source status transitions", () => {
  beforeEach(async () => {
    await resetEnvAndState()
  })

  afterEach(async () => {
    await fs.rm(TEST_DIR, { recursive: true, force: true })
  })

  test("fetch_amplitude adapter returns normalized fallback snapshot", async () => {
    const result = await fetchAmplitude({ runId: "run-v2-test" })

    expect(result.snapshot.sourceKey).toBe("amplitude")
    expect(result.snapshot.data.charts.length).toBeGreaterThan(0)
    expect(result.caveat).toContain("Using seeded Amplitude data")
  })

  test("fetch_amplitude adapter runs live chart queries sequentially", async () => {
    process.env.AMPLITUDE_API_KEY = "test-key"
    process.env.AMPLITUDE_SECRET_KEY = "test-secret"
    process.env.AMPLITUDE_CHART_IDS = "chart-a,chart-b,chart-c"
    process.env.AMPLITUDE_MAX_ATTEMPTS = "1"
    process.env.AMPLITUDE_INTER_REQUEST_DELAY_MS = "0"

    let inFlight = 0
    let maxInFlight = 0

    const result = await fetchAmplitude({
      runId: "run-v2-sequential",
      fetchImpl: async (input) => {
        const url = String(input)
        inFlight += 1
        maxInFlight = Math.max(maxInFlight, inFlight)
        await new Promise((resolve) => setTimeout(resolve, 2))
        inFlight -= 1

        const chartId = url.split("/chart/")[1]?.split("/")[0] ?? "unknown"
        return new Response(
          JSON.stringify({
            chart: { name: chartId, chart_type: "segmentation" },
            series: [1, 2, 3],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      },
    })

    expect(maxInFlight).toBe(1)
    expect(result.snapshot.data.charts.length).toBe(3)
    expect(result.caveat).toBeNull()
  })

  test("fetch_amplitude adapter retries 429 and returns partial live results", async () => {
    process.env.AMPLITUDE_API_KEY = "test-key"
    process.env.AMPLITUDE_SECRET_KEY = "test-secret"
    process.env.AMPLITUDE_CHART_IDS = "chart-retry,chart-fail"
    process.env.AMPLITUDE_MAX_ATTEMPTS = "3"
    process.env.AMPLITUDE_RETRY_BASE_DELAY_MS = "1"
    process.env.AMPLITUDE_INTER_REQUEST_DELAY_MS = "0"

    let retryAttempts = 0

    const result = await fetchAmplitude({
      runId: "run-v2-retry",
      fetchImpl: async (input) => {
        const url = String(input)
        const chartId = url.split("/chart/")[1]?.split("/")[0] ?? "unknown"

        if (chartId === "chart-retry") {
          retryAttempts += 1
          if (retryAttempts < 3) {
            return new Response(
              JSON.stringify({ error: { message: "Too many requests" } }),
              { status: 429, headers: { "Content-Type": "application/json" } }
            )
          }

          return new Response(
            JSON.stringify({
              chart: { name: "retry chart", chart_type: "segmentation" },
              series: [1, 2],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        }

        return new Response(
          JSON.stringify({ error: { message: "Too many requests" } }),
          { status: 429, headers: { "Content-Type": "application/json" } }
        )
      },
    })

    expect(retryAttempts).toBe(3)
    expect(result.snapshot.data.charts.length).toBe(1)
    expect(result.caveat).toContain("Partial Amplitude ingest")
    expect(result.caveat).toContain("chart-fail")
  })

  test("fetch_typeform adapter emits delayed-response caveat for recent window", async () => {
    const result = await fetchTypeform({ runId: "run-v2-test" })

    expect(result.snapshot.sourceKey).toBe("typeform")
    expect(result.snapshot.data.responseCount).toBeGreaterThanOrEqual(0)
    expect(result.caveat).toContain("delay very recent completed responses")
  })

  test("fetch_ios_release adapter merges local markdown fallback", async () => {
    const result = await fetchIosRelease({ runId: "run-v2-test" })

    expect(result.snapshot.sourceKey).toBe("ios_release")
    expect(result.snapshot.data.releaseNotesMarkdown.length).toBeGreaterThan(0)
    expect(result.caveat).toContain("local iOS release notes")
  })

  test("full ingest creates snapshots for all required sources", async () => {
    const result = await refreshSources()

    expect(result.statusIndex.amplitude.status).toBe("synced")
    expect(result.statusIndex.typeform.status).toBe("synced")
    expect(result.statusIndex.ios_release.status).toBe("synced")
    expect(result.sourceInventory.length).toBe(5)
  })

  test("refreshing one source updates only that source timestamp", async () => {
    const first = await refreshSources()
    const typeformTimestamp = first.statusIndex.typeform.lastSuccessAt

    await new Promise((resolve) => setTimeout(resolve, 5))

    const second = await refreshSources({ sourceKey: "amplitude" })

    expect(second.statusIndex.amplitude.lastSuccessAt).not.toBe(
      first.statusIndex.amplitude.lastSuccessAt
    )
    expect(second.statusIndex.typeform.lastSuccessAt).toBe(typeformTimestamp)
  })

  test("error in one source does not block status visibility for others", async () => {
    await refreshSources()
    const result = await refreshSources({
      sourceKey: "typeform",
      forceErrorSourceKey: "typeform",
    })

    expect(result.statusIndex.typeform.status).toBe("error")
    expect(result.statusIndex.typeform.caveat).toBeNull()
    const amplitude = result.sourceInventory.find((source) => source.id === "src-amplitude")
    expect(amplitude?.status).toBe("synced")
    expect(amplitude?.lastSync).not.toBe("Never")
  })
})
