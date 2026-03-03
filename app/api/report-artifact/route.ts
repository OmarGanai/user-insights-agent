import { NextResponse } from "next/server"
import { getReportArtifact } from "@/lib/vector/artifact-store"

export const dynamic = "force-dynamic"

export async function GET() {
  const artifact = getReportArtifact()
  return NextResponse.json({ artifact })
}
