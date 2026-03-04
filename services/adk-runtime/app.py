from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

try:
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types
except Exception as exc:  # pragma: no cover - import guard for runtime startup
    raise RuntimeError(
        "google-adk and google-genai are required. Install requirements.txt before running the runtime service."
    ) from exc


APP_NAME = "vector-adk-runtime"
USER_ID = "vector-runtime"


class CompletionSignal(BaseModel):
    status: str
    summary: str
    completedAt: str


class Evidence(BaseModel):
    id: str
    source: str
    snippet: str
    confidence: str


class ReportSection(BaseModel):
    id: str
    title: str
    content: str
    evidence: list[Evidence]


class DataSource(BaseModel):
    label: str
    detail: str
    file: str | None = None


class Hypothesis(BaseModel):
    id: str
    claim: str
    confidence: str
    supportingEvidence: list[Evidence]
    dataSources: list[DataSource]


class Recommendation(BaseModel):
    id: str
    rank: int
    title: str
    owner: str
    nextStep: str
    eta: str
    confidence: str
    evidence: list[Evidence]


class EvidenceResolution(BaseModel):
    evidenceId: str
    sourceKey: str
    sourceName: str
    snippet: str
    confidence: str
    snapshotId: str | None
    runId: str | None
    traceStepId: str | None


class PipelineStep(BaseModel):
    id: str
    name: str
    status: str
    detail: str | None = None
    outputFile: str | None = None
    outputPreview: str | None = None


class SynthesizeRequest(BaseModel):
    model: str
    state: dict[str, Any]
    runtimeContext: dict[str, Any]
    promptSnapshot: str


class SynthesizeResponse(BaseModel):
    periodLabel: str
    sections: list[ReportSection] = Field(min_length=1)
    hypotheses: list[Hypothesis] = Field(min_length=1)
    recommendations: list[Recommendation] = Field(min_length=1)
    evidenceMap: dict[str, EvidenceResolution]
    completion: CompletionSignal
    traceSteps: list[PipelineStep] = Field(min_length=1)
    backend: str
    model: str


app = FastAPI(title="Vector ADK Runtime", version="0.1.0")
session_service = InMemorySessionService()
logger = logging.getLogger(__name__)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(status_code=500, detail=f"{name} is required.")
    return value


def strip_markdown_fences(raw_text: str) -> str:
    text = raw_text.strip()
    if not text.startswith("```"):
        return text

    cleaned = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_json_object(raw_text: str) -> dict[str, Any]:
    cleaned = strip_markdown_fences(raw_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise HTTPException(status_code=502, detail="Gemini response did not contain JSON.")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="Gemini response JSON parsing failed.") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="Gemini JSON payload must be an object.")

    return parsed


def validate_contract(payload: SynthesizeResponse) -> None:
    if payload.backend != "adk_gemini":
        raise HTTPException(status_code=502, detail="Runtime payload backend must be adk_gemini.")

    if not payload.model.strip():
        raise HTTPException(status_code=502, detail="Runtime payload must include model metadata.")

    if payload.completion.status not in {"success", "partial", "blocked"}:
        raise HTTPException(
            status_code=502,
            detail="Runtime completion.status must be one of success|partial|blocked.",
        )
    if not payload.completion.summary.strip():
        raise HTTPException(status_code=502, detail="Runtime completion.summary cannot be empty.")
    if "T" not in payload.completion.completedAt:
        raise HTTPException(status_code=502, detail="Runtime completion.completedAt must be ISO-8601.")
    try:
        datetime.fromisoformat(payload.completion.completedAt.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="Runtime completion.completedAt must be ISO-8601.",
        ) from exc

    required_section_ids = {
        "sec-summary",
        "sec-metrics",
        "sec-feedback",
        "sec-releases",
        "sec-hypotheses",
        "sec-recommendations",
    }
    actual_section_ids = {section.id for section in payload.sections}
    missing = sorted(required_section_ids - actual_section_ids)
    if missing:
        raise HTTPException(
            status_code=502,
            detail=f"Runtime payload missing required section ids: {', '.join(missing)}",
        )

    required_trace_ids = {"step-synthesize", "step-complete-task"}
    actual_trace_ids = {step.id for step in payload.traceSteps}
    missing_trace_ids = sorted(required_trace_ids - actual_trace_ids)
    if missing_trace_ids:
        raise HTTPException(
            status_code=502,
            detail=f"Runtime payload missing required trace ids: {', '.join(missing_trace_ids)}",
        )


def extract_text_from_event_content(content: Any) -> str | None:
    if content is None:
        return None

    parts = getattr(content, "parts", None)
    if not parts:
        return None

    chunks: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if isinstance(text, str) and text.strip():
            chunks.append(text.strip())

    if not chunks:
        return None

    return "\n".join(chunks)


async def run_adk_synthesis(prompt: str, model_name: str, gemini_api_key: str) -> str:
    os.environ["GOOGLE_API_KEY"] = gemini_api_key

    instruction = (
        "You are Vector's synthesis runtime. "
        "Return ONLY valid JSON with no markdown and no extra keys outside the requested schema. "
        "completion.status must be one of success, partial, blocked."
    )

    agent = LlmAgent(name="vector_synthesis_agent", model=model_name, instruction=instruction)
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    session_id = f"synthesize-{uuid4().hex}"
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)

    user_message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

    final_text: str | None = None
    async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=user_message):
        if event.is_final_response():
            text = extract_text_from_event_content(getattr(event, "content", None))
            if text:
                final_text = text

    if not final_text:
        raise HTTPException(status_code=502, detail="ADK runtime returned no final response text.")

    return final_text


def build_prompt(request: SynthesizeRequest, runtime_model: str) -> str:
    state = request.state
    runtime_context = request.runtimeContext

    compact_input = {
        "runtimeContext": runtime_context,
        "promptSnapshot": request.promptSnapshot,
        "latestRun": state.get("runs", [])[-1] if isinstance(state.get("runs"), list) and state.get("runs") else None,
        "statusIndex": state.get("statusIndex", {}),
        "snapshots": state.get("snapshots", {}),
    }

    schema_description = {
        "periodLabel": "string",
        "sections": [
            {
                "id": "string",
                "title": "string",
                "content": "string",
                "evidence": [
                    {
                        "id": "string",
                        "source": "string",
                        "snippet": "string",
                        "confidence": "high|medium|low",
                    }
                ],
            }
        ],
        "hypotheses": [
            {
                "id": "string",
                "claim": "string",
                "confidence": "high|medium|low",
                "supportingEvidence": "Evidence[]",
                "dataSources": [{"label": "string", "detail": "string", "file": "string|null"}],
            }
        ],
        "recommendations": [
            {
                "id": "string",
                "rank": "number",
                "title": "string",
                "owner": "string",
                "nextStep": "string",
                "eta": "string",
                "confidence": "high|medium|low",
                "evidence": "Evidence[]",
            }
        ],
        "evidenceMap": {
            "<evidenceId>": {
                "evidenceId": "string",
                "sourceKey": "amplitude|typeform|ios_release|product_context|company_context",
                "sourceName": "string",
                "snippet": "string",
                "confidence": "high|medium|low",
                "snapshotId": "string|null",
                "runId": "string|null",
                "traceStepId": "string|null",
            }
        },
        "completion": {
            "status": "success|partial|blocked",
            "summary": "string",
            "completedAt": "ISO-8601",
        },
        "traceSteps": [
            {
                "id": "string",
                "name": "string",
                "status": "complete|running|pending|error",
                "detail": "string|null",
                "outputFile": "string|null",
                "outputPreview": "string|null",
            }
        ],
    }

    required_notes = [
        "Return plain JSON only.",
        "Include sections with ids: sec-summary, sec-metrics, sec-feedback, sec-releases, sec-hypotheses, sec-recommendations.",
        "Every evidence id referenced in sections/hypotheses/recommendations must exist in evidenceMap.",
        "Include traceSteps with ids step-synthesize and step-complete-task.",
        "Use completion.status=partial or blocked when source coverage is incomplete or blocked.",
    ]

    return "\n\n".join(
        [
            f"Runtime model: {runtime_model}",
            "Task: Synthesize a weekly decision brief from runtime input.",
            f"Contract schema (JSON): {json.dumps(schema_description, ensure_ascii=True)}",
            f"Rules: {json.dumps(required_notes, ensure_ascii=True)}",
            f"Runtime input: {json.dumps(compact_input, ensure_ascii=True)}",
        ]
    )


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "backend": "adk_gemini"}


@app.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(
    request: SynthesizeRequest,
    x_gemini_api_key: str | None = Header(default=None, alias="X-Gemini-Api-Key"),
) -> SynthesizeResponse:
    gemini_api_key = required_env("GEMINI_API_KEY")
    runtime_model = required_env("GEMINI_MODEL")

    if x_gemini_api_key and x_gemini_api_key != gemini_api_key:
        raise HTTPException(status_code=401, detail="X-Gemini-Api-Key does not match runtime config.")

    if request.model.strip() and request.model.strip() != runtime_model:
        raise HTTPException(
            status_code=400,
            detail="Request model must match configured GEMINI_MODEL.",
        )

    try:
        prompt = build_prompt(request, runtime_model)
        raw_text = await run_adk_synthesis(prompt=prompt, model_name=runtime_model, gemini_api_key=gemini_api_key)
        parsed = parse_json_object(raw_text)

        parsed["backend"] = "adk_gemini"
        parsed["model"] = runtime_model

        payload = SynthesizeResponse(**parsed)
        validate_contract(payload)
        return payload
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard for upstream SDK/runtime failures
        logger.exception("ADK runtime synthesis failed")
        raise HTTPException(
            status_code=502,
            detail=f"ADK synthesis upstream failure: {type(exc).__name__}: {exc}",
        ) from exc
