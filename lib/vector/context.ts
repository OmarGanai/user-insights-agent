import { promises as fs } from "node:fs"
import crypto from "node:crypto"
import path from "node:path"
import {
  COMPANY_CONTEXT_FILE,
  PRODUCT_CONTEXT_FILE,
  sourceDefinitionForKey,
  sourceIdFromKey,
} from "@/lib/vector/constants"
import { isoNow } from "@/lib/vector/time"
import type { NormalizedSourceSnapshot } from "@/lib/vector/types"

interface ContextDoc {
  path: string
  content: string
  versionHash: string
  modifiedAt: string
}

async function readContextDocument(relativePath: string): Promise<ContextDoc> {
  const absolutePath = path.join(process.cwd(), relativePath)
  const [content, stat] = await Promise.all([
    fs.readFile(absolutePath, "utf8"),
    fs.stat(absolutePath),
  ])

  const versionHash = crypto.createHash("sha1").update(content).digest("hex").slice(0, 12)

  return {
    path: relativePath,
    content,
    versionHash,
    modifiedAt: stat.mtime.toISOString(),
  }
}

function toSnapshot(
  runId: string,
  sourceKey: "product_context" | "company_context",
  doc: ContextDoc
): NormalizedSourceSnapshot<{
  filePath: string
  content: string
  versionHash: string
  modifiedAt: string
}> {
  const source = sourceDefinitionForKey(sourceKey)
  return {
    id: `${source.id}-${runId}`,
    sourceKey,
    sourceId: sourceIdFromKey(sourceKey),
    runId,
    capturedAt: isoNow(),
    summary: `${source.name} loaded (${doc.versionHash})`,
    recordCount: 1,
    data: {
      filePath: doc.path,
      content: doc.content,
      versionHash: doc.versionHash,
      modifiedAt: doc.modifiedAt,
    },
  }
}

export async function loadContextSnapshots(runId: string): Promise<
  Array<
    NormalizedSourceSnapshot<{
      filePath: string
      content: string
      versionHash: string
      modifiedAt: string
    }>
  >
> {
  const [product, company] = await Promise.all([
    readContextDocument(PRODUCT_CONTEXT_FILE),
    readContextDocument(COMPANY_CONTEXT_FILE),
  ])

  return [
    toSnapshot(runId, "product_context", product),
    toSnapshot(runId, "company_context", company),
  ]
}

export function extractVocabularyFromContext(content: string): string[] {
  const lines = content.split("\n")
  const words: string[] = []
  let inVocabulary = false

  for (const line of lines) {
    const trimmed = line.trim()
    if (/^##\s+Vocabulary/i.test(trimmed)) {
      inVocabulary = true
      continue
    }

    if (inVocabulary && /^##\s+/.test(trimmed)) {
      break
    }

    if (inVocabulary && trimmed.startsWith("-")) {
      const [term] = trimmed.slice(1).split(":")
      const cleaned = term.trim()
      if (cleaned.length > 0) {
        words.push(cleaned)
      }
    }
  }

  return words
}
