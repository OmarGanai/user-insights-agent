import { NextResponse } from "next/server"
import { ensureInitialIngest } from "@/lib/vector/ingest"
import { writeReportDraft } from "@/lib/vector/workflows"

export const dynamic = "force-dynamic"

export async function POST() {
  await ensureInitialIngest()
  const { artifact, trace } = await writeReportDraft()
  return NextResponse.json({ artifact, trace })
}
