import { NextRequest, NextResponse } from "next/server"
import { getReportArtifact, savePublishMetadata, writeReportDraft } from "@/lib/vector/workflows"
import { postSlackMessage } from "@/lib/vector/publish"
import { renderBlockkitPreview } from "@/lib/vector/slack"

interface PublishRequestBody {
  dryRun?: boolean
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json().catch(() => ({}))) as PublishRequestBody
    let artifact = await getReportArtifact()

    if (!artifact) {
      artifact = (await writeReportDraft()).artifact
    }

    const payload = renderBlockkitPreview(artifact)
    const destinationLabel = process.env.SLACK_CHANNEL || "#product-updates"

    const publishMetadata = await postSlackMessage({
      payload,
      destinationLabel,
      dryRun: Boolean(body.dryRun),
    })

    await savePublishMetadata(publishMetadata)

    const statusCode = publishMetadata.status === "success" ? 200 : 502
    return NextResponse.json(
      {
        artifactId: artifact.id,
        payload,
        publishMetadata,
      },
      { status: statusCode }
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : "Publish failed."
    const status =
      message.includes("ADK runtime") ||
      message.includes("ADK_RUNTIME_URL") ||
      message.includes("GEMINI_")
        ? 503
        : 500

    return NextResponse.json({ error: message }, { status })
  }
}
