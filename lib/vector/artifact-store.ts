import {
  MOCK_HYPOTHESES,
  MOCK_RECOMMENDATIONS,
  MOCK_REPORT_SECTIONS,
  type ReportSection,
} from "@/lib/mock-data"
import type { PublishMetadata, ReportArtifact } from "@/lib/vector/types"

const INITIAL_ARTIFACT_ID = "artifact-weekly-2026-03-02"
const INITIAL_PERIOD_LABEL = "Feb 24 - Mar 2, 2026"

const globalStore = globalThis as typeof globalThis & {
  vectorReportArtifact?: ReportArtifact
}

function createInitialArtifact(): ReportArtifact {
  const now = new Date().toISOString()
  return {
    id: INITIAL_ARTIFACT_ID,
    periodLabel: INITIAL_PERIOD_LABEL,
    sections: structuredClone(MOCK_REPORT_SECTIONS),
    hypotheses: structuredClone(MOCK_HYPOTHESES),
    recommendations: structuredClone(MOCK_RECOMMENDATIONS),
    evidenceMap: {},
    runMetadata: {
      runId: "seeded-run",
      generatedAt: now,
      completion: {
        status: "success",
        summary: "Seeded artifact initialized for compatibility paths.",
        completedAt: now,
      },
      runtimeContext: {
        sourceInventory: [],
        capabilityMap: [],
        vocabulary: [],
        recentRunState: {
          runId: null,
          completedAt: null,
          statusSummary: "seeded",
        },
      },
      promptSnapshot: "Seeded artifact compatibility snapshot.",
      traceId: "seeded-trace",
      traceStepIds: [],
    },
    edits: [],
    updatedAt: now,
    publishMetadata: null,
  }
}

function ensureArtifact(): ReportArtifact {
  if (!globalStore.vectorReportArtifact) {
    globalStore.vectorReportArtifact = createInitialArtifact()
  }
  return globalStore.vectorReportArtifact
}

export function getReportArtifact(): ReportArtifact {
  return ensureArtifact()
}

export function updateReportSection(sectionId: string, content: string): ReportArtifact {
  const artifact = ensureArtifact()
  const sectionExists = artifact.sections.some((section) => section.id === sectionId)

  if (!sectionExists) {
    throw new Error(`Unknown section id: ${sectionId}`)
  }

  artifact.sections = artifact.sections.map((section: ReportSection) =>
    section.id === sectionId ? { ...section, content } : section
  )
  artifact.updatedAt = new Date().toISOString()
  return artifact
}

export function savePublishMetadata(metadata: PublishMetadata): ReportArtifact {
  const artifact = ensureArtifact()
  artifact.publishMetadata = metadata
  artifact.updatedAt = new Date().toISOString()
  return artifact
}
