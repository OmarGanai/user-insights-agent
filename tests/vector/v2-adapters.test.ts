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
    const amplitude = result.sourceInventory.find((source) => source.id === "src-amplitude")
    expect(amplitude?.status).toBe("synced")
    expect(amplitude?.lastSync).not.toBe("Never")
  })
})
