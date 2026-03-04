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
const MOCK_RUNTIME_URL = "http://adk-runtime.test"
const ORIGINAL_FETCH = globalThis.fetch

type CompletionStatus = "success" | "partial" | "blocked"

interface RuntimeRequestCapture {
  headers: Record<string, string>
  body: Record<string, unknown>
}

interface BuildRuntimePayloadOptions {
  completionStatus?: CompletionStatus | string
  completionSummary?: string
  backend?: string
  model?: string
}

let runtimeRequests: RuntimeRequestCapture[] = []
let runtimePayloadFactory: () => Record<string, unknown> = () => buildRuntimePayload()

function buildRuntimePayload(options: BuildRuntimePayloadOptions = {}): Record<string, unknown> {
  const completionStatus = options.completionStatus ?? "success"
  const completionSummary =
    options.completionSummary ?? "Runtime synthesis completed with full source coverage."
  const completionStepStatus =
    completionStatus === "blocked" ? "error" : completionStatus === "partial" ? "running" : "complete"

  const sharedEvidence = {
    id: "ev-runtime-1",
    source: "Amplitude",
    snippet: "Activation rate improved after onboarding copy update.",
    confidence: "high",
  }

  return {
    periodLabel: "Mar 1 - Mar 7, 2026",
    sections: [
      {
        id: "sec-summary",
        title: "Executive Summary",
        content: "Activation improved while retention remains flat.",
        evidence: [sharedEvidence],
      },
      {
        id: "sec-metrics",
        title: "Key Metrics & Top Movers",
        content: "Activation +6%, D7 retention flat, trial conversion +2%.",
        evidence: [sharedEvidence],
      },
      {
        id: "sec-feedback",
        title: "User Feedback Themes",
        content: "Onboarding clarity requests declined in the latest survey batch.",
        evidence: [sharedEvidence],
      },
      {
        id: "sec-releases",
        title: "Release Impact",
        content: "Latest release reduced crash reports but did not move retention yet.",
        evidence: [sharedEvidence],
      },
      {
        id: "sec-hypotheses",
        title: "Hypotheses",
        content: "",
        evidence: [],
      },
      {
        id: "sec-recommendations",
        title: "Recommendations",
        content: "",
        evidence: [],
      },
    ],
    hypotheses: [
      {
        id: "hyp-runtime-1",
        claim:
          "Improved first-session clarity is lifting activation, but retention impact needs follow-up experiments.",
        confidence: "high",
        supportingEvidence: [sharedEvidence],
        dataSources: [
          {
            label: "Amplitude Activation Funnel",
            detail: "Activation completion moved from 42% to 48% week-over-week.",
            file: "snapshot-amplitude-1",
          },
        ],
      },
    ],
    recommendations: [
      {
        id: "rec-runtime-1",
        rank: 1,
        title: "Run retention-focused onboarding follow-up",
        owner: "Product",
        nextStep: "Test post-activation nudge messaging for week-one engagement.",
        eta: "1 week",
        confidence: "high",
        evidence: [sharedEvidence],
      },
    ],
    evidenceMap: {
      "ev-runtime-1": {
        evidenceId: "ev-runtime-1",
        sourceKey: "amplitude",
        sourceName: "Amplitude",
        snippet: "Activation rate improved after onboarding copy update.",
        confidence: "high",
        snapshotId: "snapshot-amplitude-1",
        runId: "run-runtime-1",
        traceStepId: "step-ingest-amplitude",
      },
    },
    completion: {
      status: completionStatus,
      summary: completionSummary,
      completedAt: "2026-03-03T12:00:00.000Z",
    },
    traceSteps: [
      {
        id: "step-synthesize",
        name: "Synthesize draft",
        status: "complete",
        detail: "ADK runtime generated sections and recommendations.",
      },
      {
        id: "step-complete-task",
        name: "complete_task",
        status: completionStepStatus,
        detail: `complete_task status=${completionStatus}`,
        outputPreview: completionSummary,
      },
    ],
    backend: options.backend ?? "adk_gemini",
    model: options.model ?? (process.env.GEMINI_MODEL ?? "gemini-3-flash-preview"),
  }
}

function normalizeHeaders(headers: HeadersInit | undefined): Record<string, string> {
  const result: Record<string, string> = {}
  if (!headers) {
    return result
  }

  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      result[key.toLowerCase()] = value
    })
    return result
  }

  if (Array.isArray(headers)) {
    for (const [key, value] of headers) {
      result[key.toLowerCase()] = String(value)
    }
    return result
  }

  for (const [key, value] of Object.entries(headers)) {
    if (typeof value !== "undefined") {
      result[key.toLowerCase()] = String(value)
    }
  }

  return result
}

function parseRequestBody(body: BodyInit | null | undefined): Record<string, unknown> {
  if (typeof body !== "string") {
    return {}
  }

  try {
    const parsed = JSON.parse(body) as unknown
    if (parsed && typeof parsed === "object") {
      return parsed as Record<string, unknown>
    }
  } catch {
    return {}
  }

  return {}
}

function requestUrlFromInput(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input
  }

  if (input instanceof URL) {
    return input.toString()
  }

  if (input instanceof Request) {
    return input.url
  }

  return ""
}

async function resetEnvAndState() {
  process.env.VECTOR_DATA_DIR = TEST_DIR
  delete process.env.AMPLITUDE_API_KEY
  delete process.env.AMPLITUDE_SECRET_KEY
  delete process.env.AMPLITUDE_CHART_IDS
  delete process.env.TYPEFORM_API_KEY
  delete process.env.TYPEFORM_FORM_ID
  delete process.env.IOS_APP_ID
  process.env.ADK_RUNTIME_URL = MOCK_RUNTIME_URL
  process.env.GEMINI_API_KEY = "test-gemini-key"
  process.env.GEMINI_MODEL = "gemini-3-flash-preview"
  await fs.rm(TEST_DIR, { recursive: true, force: true })
  await resetVectorStateForTests()
}

describe("V3 synthesis artifact and evidence trace", () => {
  beforeEach(async () => {
    await resetEnvAndState()
    runtimePayloadFactory = () => buildRuntimePayload()
    runtimeRequests = []

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrlFromInput(input)
      if (url === `${MOCK_RUNTIME_URL}/synthesize`) {
        runtimeRequests.push({
          headers: normalizeHeaders(init?.headers),
          body: parseRequestBody(init?.body),
        })

        return new Response(JSON.stringify(runtimePayloadFactory()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      }

      return ORIGINAL_FETCH(input, init)
    }) as typeof fetch

    await refreshSources()
  })

  afterEach(async () => {
    globalThis.fetch = ORIGINAL_FETCH
    delete process.env.ADK_RUNTIME_URL
    delete process.env.GEMINI_API_KEY
    delete process.env.GEMINI_MODEL
    await fs.rm(TEST_DIR, { recursive: true, force: true })
  })

  test("write_report_draft persists runtime identity and completion metadata", async () => {
    const { artifact, trace } = await writeReportDraft()

    expect(runtimeRequests.length).toBe(1)
    expect(runtimeRequests[0]?.headers["x-gemini-api-key"]).toBe("test-gemini-key")
    expect(runtimeRequests[0]?.body.model).toBe("gemini-3-flash-preview")

    const sectionIds = artifact.sections.map((section) => section.id)
    expect(sectionIds).toContain("sec-summary")
    expect(sectionIds).toContain("sec-metrics")
    expect(sectionIds).toContain("sec-feedback")
    expect(sectionIds).toContain("sec-releases")

    expect(artifact.runMetadata.completion.status).toBe("success")
    expect(artifact.runMetadata.completion.summary).toBe(
      "Runtime synthesis completed with full source coverage."
    )
    expect(artifact.runMetadata.backend).toBe("adk_gemini")
    expect(artifact.runMetadata.model).toBe("gemini-3-flash-preview")

    expect(Object.keys(artifact.evidenceMap).length).toBeGreaterThan(0)
    expect(trace.steps.some((step) => step.id === "step-complete-task")).toBe(true)
    expect(trace.promptSnapshot).toContain("Completion contract")
  })

  test("completion semantics are sourced from runtime payload", async () => {
    runtimePayloadFactory = () =>
      buildRuntimePayload({
        completionStatus: "partial",
        completionSummary: "Runtime marked this run partial due stale Typeform coverage.",
      })

    const { artifact, trace } = await writeReportDraft()

    expect(artifact.runMetadata.completion.status).toBe("partial")
    expect(artifact.runMetadata.completion.summary).toBe(
      "Runtime marked this run partial due stale Typeform coverage."
    )
    expect(trace.steps.find((step) => step.id === "step-complete-task")?.detail).toBe(
      "complete_task status=partial"
    )
  })

  test("runtime identity gate rejects non-ADK backend responses", async () => {
    runtimePayloadFactory = () => buildRuntimePayload({ backend: "legacy_runtime" })

    await expect(writeReportDraft()).rejects.toThrow("non-ADK backend")
  })

  test("completion contract gate rejects invalid runtime status", async () => {
    runtimePayloadFactory = () => buildRuntimePayload({ completionStatus: "completed" })

    await expect(writeReportDraft()).rejects.toThrow("invalid completion status")
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

  test("write_report_draft fails fast when ADK runtime config is missing", async () => {
    delete process.env.ADK_RUNTIME_URL
    await expect(writeReportDraft()).rejects.toThrow("ADK_RUNTIME_URL")
  })
})
