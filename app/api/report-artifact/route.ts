import { NextResponse } from "next/server"
import { ensureInitialIngest } from "@/lib/vector/ingest"
import { getReportArtifact, writeReportDraft } from "@/lib/vector/workflows"

export const dynamic = "force-dynamic"

export async function GET() {
  try {
    await ensureInitialIngest()
    let artifact = await getReportArtifact()

    if (!artifact) {
      artifact = (await writeReportDraft()).artifact
    }

    return NextResponse.json({ artifact })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Report fetch failed."
    const status =
      message.includes("ADK runtime") ||
      message.includes("ADK_RUNTIME_URL") ||
      message.includes("GEMINI_")
        ? 503
        : 500

    return NextResponse.json({ error: message }, { status })
  }
}
