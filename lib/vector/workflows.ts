import {
  getEvidenceForClaimPrimitive,
  getLatestTracePrimitive,
  getReportArtifactPrimitive,
  savePublishMetadataPrimitive,
  updateReportSectionPrimitive,
  writeReportDraftPrimitive,
} from "@/lib/vector/primitives"
import type { PublishMetadata } from "@/lib/vector/types"

/**
 * Primitive-first contract:
 * - Workflow helpers are thin delegators and never embed domain decisions.
 * - Source-of-truth behavior remains in primitive implementations.
 */
export async function writeReportDraft() {
  return writeReportDraftPrimitive()
}

export async function getReportArtifact() {
  return getReportArtifactPrimitive()
}

export async function updateReportSection(sectionId: string, content: string) {
  return updateReportSectionPrimitive(sectionId, content)
}

export async function getEvidenceForClaim(evidenceId: string) {
  return getEvidenceForClaimPrimitive(evidenceId)
}

export async function getLatestTrace() {
  return getLatestTracePrimitive()
}

export async function savePublishMetadata(metadata: PublishMetadata) {
  return savePublishMetadataPrimitive(metadata)
}
