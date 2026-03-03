import type { Hypothesis, Recommendation, ReportSection } from "@/lib/mock-data"

export type PublishResultStatus = "success" | "failed"
export type PublishMode = "webhook" | "dry_run"

export interface PublishMetadata {
  attemptedAt: string
  destinationLabel: string
  status: PublishResultStatus
  mode: PublishMode
  error?: string
  httpStatus?: number
}

export interface ReportArtifact {
  id: string
  periodLabel: string
  sections: ReportSection[]
  hypotheses: Hypothesis[]
  recommendations: Recommendation[]
  updatedAt: string
  publishMetadata: PublishMetadata | null
}

export interface SlackTextObject {
  type: "mrkdwn" | "plain_text"
  text: string
}

export type SlackBlock =
  | { type: "header"; text: SlackTextObject }
  | { type: "section"; text: SlackTextObject }
  | { type: "context"; elements: SlackTextObject[] }
  | { type: "divider" }

export interface SlackPayload {
  text: string
  blocks: SlackBlock[]
}
