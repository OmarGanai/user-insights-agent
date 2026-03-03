import { NextResponse } from "next/server"
import { ensureInitialIngest } from "@/lib/vector/ingest"
import { getReportArtifact, writeReportDraft } from "@/lib/vector/workflows"

export const dynamic = "force-dynamic"

export async function GET() {
  await ensureInitialIngest()
  let artifact = await getReportArtifact()

  if (!artifact) {
    artifact = (await writeReportDraft()).artifact
  }

  return NextResponse.json({ artifact })
}
