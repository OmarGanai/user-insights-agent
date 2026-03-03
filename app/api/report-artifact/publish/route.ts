import { NextRequest, NextResponse } from "next/server"
import { getReportArtifact, savePublishMetadata } from "@/lib/vector/artifact-store"
import { postSlackMessage } from "@/lib/vector/publish"
import { renderBlockkitPreview } from "@/lib/vector/slack"

interface PublishRequestBody {
  dryRun?: boolean
}

export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => ({}))) as PublishRequestBody
  const artifact = getReportArtifact()
  const payload = renderBlockkitPreview(artifact)
  const destinationLabel = process.env.SLACK_CHANNEL || "#product-updates"

  const publishMetadata = await postSlackMessage({
    payload,
    destinationLabel,
    dryRun: Boolean(body.dryRun),
  })

  savePublishMetadata(publishMetadata)

  const statusCode = publishMetadata.status === "success" ? 200 : 502
  return NextResponse.json(
    {
      artifactId: artifact.id,
      payload,
      publishMetadata,
    },
    { status: statusCode }
  )
}
