import { NextResponse } from "next/server"
import { getReportArtifact, writeReportDraft } from "@/lib/vector/workflows"
import { renderBlockkitPreview } from "@/lib/vector/slack"

export const dynamic = "force-dynamic"

export async function GET() {
  try {
    let artifact = await getReportArtifact()
    if (!artifact) {
      artifact = (await writeReportDraft()).artifact
    }

    const payload = renderBlockkitPreview(artifact)

    return NextResponse.json({
      artifactId: artifact.id,
      generatedAt: new Date().toISOString(),
      payload,
      publishMetadata: artifact.publishMetadata,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Preview generation failed."
    const status =
      message.includes("ADK runtime") ||
      message.includes("ADK_RUNTIME_URL") ||
      message.includes("GEMINI_")
        ? 503
        : 500

    return NextResponse.json({ error: message }, { status })
  }
}
