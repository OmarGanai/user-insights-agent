import type { Hypothesis, PipelineStep, Recommendation, ReportSection } from "@/lib/mock-data"
import type {
  CompletionSignal,
  EvidenceResolution,
  RuntimeBackend,
  RuntimeContextPayload,
  VectorState,
} from "@/lib/vector/types"

interface AgentRuntimeSynthesisPayload {
  periodLabel: string
  sections: ReportSection[]
  hypotheses: Hypothesis[]
  recommendations: Recommendation[]
  evidenceMap: Record<string, EvidenceResolution>
  completion: CompletionSignal
  traceSteps: PipelineStep[]
  backend: RuntimeBackend
  model: string
}

interface SynthesizeViaRuntimeArgs {
  state: VectorState
  runtimeContext: RuntimeContextPayload
  promptSnapshot: string
}

export class AgentRuntimeError extends Error {
  constructor(
    message: string,
    public readonly status: number | null = null
  ) {
    super(message)
    this.name = "AgentRuntimeError"
  }
}

function requiredEnv(name: string): string {
  const value = process.env[name]?.trim()
  if (!value) {
    throw new AgentRuntimeError(`${name} is required for ADK + Gemini synthesis.`, null)
  }
  return value
}

function synthesizeEndpoint(baseUrl: string): string {
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`
  return new URL("synthesize", normalizedBase).toString()
}

function assertRuntimePayload(payload: unknown): AgentRuntimeSynthesisPayload {
  if (!payload || typeof payload !== "object") {
    throw new AgentRuntimeError("ADK runtime returned invalid payload (expected object).")
  }

  const candidate = payload as Partial<AgentRuntimeSynthesisPayload>

  if (candidate.backend !== "adk_gemini") {
    throw new AgentRuntimeError("ADK runtime returned non-ADK backend response.")
  }

  if (typeof candidate.model !== "string" || candidate.model.length === 0) {
    throw new AgentRuntimeError("ADK runtime payload is missing model metadata.")
  }

  if (!Array.isArray(candidate.sections)) {
    throw new AgentRuntimeError("ADK runtime payload is missing sections.")
  }

  if (!Array.isArray(candidate.hypotheses) || !Array.isArray(candidate.recommendations)) {
    throw new AgentRuntimeError("ADK runtime payload is missing hypotheses/recommendations.")
  }

  if (!candidate.completion || typeof candidate.completion !== "object") {
    throw new AgentRuntimeError("ADK runtime payload is missing completion signal.")
  }

  if (!Array.isArray(candidate.traceSteps)) {
    throw new AgentRuntimeError("ADK runtime payload is missing trace steps.")
  }

  if (!candidate.evidenceMap || typeof candidate.evidenceMap !== "object") {
    throw new AgentRuntimeError("ADK runtime payload is missing evidence map.")
  }

  if (typeof candidate.periodLabel !== "string" || candidate.periodLabel.length === 0) {
    throw new AgentRuntimeError("ADK runtime payload is missing period label.")
  }

  return candidate as AgentRuntimeSynthesisPayload
}

export async function synthesizeViaAgentRuntime({
  state,
  runtimeContext,
  promptSnapshot,
}: SynthesizeViaRuntimeArgs): Promise<AgentRuntimeSynthesisPayload> {
  const runtimeUrl = requiredEnv("ADK_RUNTIME_URL")
  const geminiApiKey = requiredEnv("GEMINI_API_KEY")
  const geminiModel = requiredEnv("GEMINI_MODEL")

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 30000)

  try {
    const response = await fetch(synthesizeEndpoint(runtimeUrl), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Gemini-Api-Key": geminiApiKey,
      },
      body: JSON.stringify({
        model: geminiModel,
        state,
        runtimeContext,
        promptSnapshot,
      }),
      signal: controller.signal,
      cache: "no-store",
    })

    if (!response.ok) {
      const body = await response.text()
      throw new AgentRuntimeError(
        `ADK runtime synthesis failed (${response.status}): ${body || "unknown error"}`,
        response.status
      )
    }

    const payload = (await response.json()) as unknown
    return assertRuntimePayload(payload)
  } catch (error) {
    if (error instanceof AgentRuntimeError) {
      throw error
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new AgentRuntimeError("ADK runtime synthesis timed out after 30 seconds.", 504)
    }

    const message = error instanceof Error ? error.message : "unknown runtime error"
    throw new AgentRuntimeError(`ADK runtime synthesis request failed: ${message}`)
  } finally {
    clearTimeout(timeout)
  }
}
