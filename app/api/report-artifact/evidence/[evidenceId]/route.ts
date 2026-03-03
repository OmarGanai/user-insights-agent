import { NextResponse } from "next/server"
import { getEvidenceForClaim } from "@/lib/vector/workflows"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ evidenceId: string }> }
) {
  const evidenceId = (await params).evidenceId

  try {
    const evidence = await getEvidenceForClaim(evidenceId)
    return NextResponse.json({ evidence })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown evidence lookup error"
    return NextResponse.json({ error: message }, { status: 404 })
  }
}
