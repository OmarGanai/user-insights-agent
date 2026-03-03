import { NextResponse } from "next/server"
import { getReportArtifact, writeReportDraft } from "@/lib/vector/workflows"
import { renderBlockkitPreview } from "@/lib/vector/slack"

export const dynamic = "force-dynamic"

export async function GET() {
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
}
