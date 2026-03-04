import { NextResponse } from "next/server"
import { ensureInitialIngest } from "@/lib/vector/ingest"
import { writeReportDraft } from "@/lib/vector/workflows"

export const dynamic = "force-dynamic"

export async function POST() {
  try {
    await ensureInitialIngest()
    const { artifact, trace } = await writeReportDraft()
    return NextResponse.json({ artifact, trace })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Report generation failed."
    const status =
      message.includes("ADK runtime") ||
      message.includes("ADK_RUNTIME_URL") ||
      message.includes("GEMINI_")
        ? 503
        : 500

    return NextResponse.json({ error: message }, { status })
  }
}
