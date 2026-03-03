import { NextResponse } from "next/server"
import { getReportArtifact } from "@/lib/vector/artifact-store"
import { renderBlockkitPreview } from "@/lib/vector/slack"

export const dynamic = "force-dynamic"

export async function GET() {
  const artifact = getReportArtifact()
  const payload = renderBlockkitPreview(artifact)

  return NextResponse.json({
    artifactId: artifact.id,
    generatedAt: new Date().toISOString(),
    payload,
    publishMetadata: artifact.publishMetadata,
  })
}
