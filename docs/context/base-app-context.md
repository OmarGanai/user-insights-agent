# Base App Context

tenant is a household planning product focused on helping users coordinate home life through DENTS (Documents, Events, Notes, Tasks), calendar integrations, appliance management, and shared household collaboration.

## Product Shape

- Core surfaces: Home, Life, Time, People, AI chat
- Activation-critical actions include doing a braindump, calendar setup, DENT creation, appliance setup, and inviting household members.
- Current weekly reporting must remain evidence-first with explicit percentages and absolute counts.

## In-App Route Glossary

Use this mapping when route/path strings appear in events, diagnostics, or release notes.

| Surface | Canonical route(s) | Meaning |
| --- | --- | --- |
| Home | `/home` | Dashboard: Today/What's Next, pinned items, recent activity |
| Life | `/life` | Household management hub (tiles, spaces, appliances, utilities) |
| Time | `/time` | Calendar and scheduling |
| People | `/people` | Household members and contacts |
| AI chat | `/assistant-chat` | tenant assistant chat entry point |

| Domain | Route patterns | Meaning |
| --- | --- | --- |
| Tasks | `/create-task`, `/edit-task/[id]`, `/view-task/[id]` | Task create/edit/view flow |
| Events | `/create-event`, `/edit-event/[id]`, `/view-event/[id]` | Event create/edit/view flow |
| Notes | `/create-note`, `/edit-note/[id]`, `/view-note/[id]` | Note create/edit/view flow |
| Documents | `/create-doc`, `/edit-document`, `/document-viewer` | Document upload/edit/view flow |
| Life tiles | `/tile/[id]`, `/spaces`, `/space-detail/[id]`, `/appliances`, `/appliance-detail/[id]`, `/utilities`, `/utility-detail/[type]` | Life sub-navigation |
| People detail | `/people/[id]`, `/people/new`, `/people/[id]/edit` | Contact/member management |
| Hive | `/my-hive`, `/my-hive/member/[id]`, `/hive-selection` | Household membership management |
| Global utilities | `/search`, `/settings`, `/profile`, `/profile/edit`, `/calendars` | Cross-surface utility screens |

## Path Interpretation Rules

- Bracketed segments (for example `[id]`, `[type]`) are dynamic parameters, not literal strings.
- When only a route prefix is known, infer the domain by prefix:
  - `/create-*`, `/edit-*`, `/view-*` map to DENT lifecycle actions.
  - `/tile`, `/space`, `/appliance`, `/utilities` map to Life domain actions.
  - `/people` and `/my-hive` map to collaboration/contact actions.
- In mobile WebView mode, `?mobile=true` hides web tab UI and `?token=` carries auth; these query params do not change route meaning.
- Route-level diagnostics are supportive context; activation decisioning should stay anchored to validated business events/charts.

## Reporting Guardrails

- Use only tenant-prod Amplitude project (`appId=639837`).
- Exclude employee cohort with segment `userdata_cohort is not 5cn1caqx`.
- Keep report narrative grounded in chart evidence and avoid speculative claims when counts are low.
