import { afterEach, beforeEach, describe, expect, test } from "bun:test"
import { promises as fs } from "node:fs"
import path from "node:path"
import { refreshSources } from "@/lib/vector/ingest"
import { resetVectorStateForTests } from "@/lib/vector/store"
import {
  getEvidenceForClaim,
  getLatestTrace,
  getReportArtifact,
  updateReportSection,
  writeReportDraft,
} from "@/lib/vector/workflows"

const TEST_DIR = path.join(process.cwd(), ".tmp-vector-tests", "v3")

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

describe("V3 synthesis artifact and evidence trace", () => {
  beforeEach(async () => {
    await resetEnvAndState()
    await refreshSources()
  })

  afterEach(async () => {
    await fs.rm(TEST_DIR, { recursive: true, force: true })
  })

  test("write_report_draft produces required sections with explicit completion signal", async () => {
    const { artifact, trace } = await writeReportDraft()

    const sectionIds = artifact.sections.map((section) => section.id)
    expect(sectionIds).toContain("sec-summary")
    expect(sectionIds).toContain("sec-metrics")
    expect(sectionIds).toContain("sec-feedback")
    expect(sectionIds).toContain("sec-releases")

    expect(artifact.runMetadata.completion.status).toBe("success")
    expect(artifact.runMetadata.completion.summary.length).toBeGreaterThan(0)

    expect(Object.keys(artifact.evidenceMap).length).toBeGreaterThan(0)
    expect(trace.steps.some((step) => step.id === "step-complete-task")).toBe(true)
    expect(trace.promptSnapshot).toContain("Completion contract")
  })

  test("update_report_section persists edits across reads", async () => {
    const { artifact } = await writeReportDraft()
    const targetSection = artifact.sections[0]
    const updated = await updateReportSection(targetSection.id, "Updated section content")

    expect(updated.sections.find((section) => section.id === targetSection.id)?.content).toBe(
      "Updated section content"
    )

    const persisted = await getReportArtifact()
    expect(persisted?.sections.find((section) => section.id === targetSection.id)?.content).toBe(
      "Updated section content"
    )
    expect((persisted?.edits.length ?? 0) > 0).toBe(true)
  })

  test("evidence resolver and latest trace expose provenance", async () => {
    const { artifact } = await writeReportDraft()
    const evidenceId = Object.keys(artifact.evidenceMap)[0]

    const evidence = await getEvidenceForClaim(evidenceId)
    expect(evidence.evidenceId).toBe(evidenceId)
    expect(evidence.sourceName.length).toBeGreaterThan(0)

    const trace = await getLatestTrace()
    expect(trace).not.toBeNull()
    expect(trace?.steps.length).toBeGreaterThan(0)
    expect(trace?.promptSnapshot).toContain("Capability map")
  })
})
