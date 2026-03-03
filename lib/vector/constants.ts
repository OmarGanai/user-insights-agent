import type { SourceDefinition, VectorSourceId, VectorSourceKey } from "@/lib/vector/types"

export const SOURCE_DEFINITIONS: SourceDefinition[] = [
  { key: "amplitude", id: "src-amplitude", name: "Amplitude", type: "amplitude" },
  { key: "typeform", id: "src-typeform", name: "Typeform", type: "typeform" },
  { key: "ios_release", id: "src-ios", name: "iOS Releases", type: "ios_release" },
  {
    key: "product_context",
    id: "src-product-context",
    name: "Product Context",
    type: "product_context",
  },
  {
    key: "company_context",
    id: "src-company-context",
    name: "Company Context",
    type: "company_context",
  },
]

export const REQUIRED_LIVE_SOURCE_KEYS: VectorSourceKey[] = ["amplitude", "typeform", "ios_release"]

export const DEFAULT_VECTOR_DATA_DIR = ".vector-data"

export const PRODUCT_CONTEXT_FILE = "data/vector/product-context.md"
export const COMPANY_CONTEXT_FILE = "data/vector/company-context.md"
export const IOS_RELEASE_NOTES_FILE = "data/vector/ios-release-notes.md"

const keyById = new Map<VectorSourceId, VectorSourceKey>(
  SOURCE_DEFINITIONS.map((source) => [source.id, source.key])
)

const idByKey = new Map<VectorSourceKey, VectorSourceId>(
  SOURCE_DEFINITIONS.map((source) => [source.key, source.id])
)

export function sourceKeyFromId(id: string): VectorSourceKey | null {
  return keyById.get(id as VectorSourceId) ?? null
}

export function sourceIdFromKey(key: VectorSourceKey): VectorSourceId {
  const sourceId = idByKey.get(key)
  if (!sourceId) {
    throw new Error(`No source id mapped for key: ${key}`)
  }
  return sourceId
}

export function sourceDefinitionForKey(key: VectorSourceKey): SourceDefinition {
  const definition = SOURCE_DEFINITIONS.find((source) => source.key === key)
  if (!definition) {
    throw new Error(`Unknown source key: ${key}`)
  }
  return definition
}
