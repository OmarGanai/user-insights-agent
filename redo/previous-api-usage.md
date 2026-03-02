# Amplitude Insights Bot – API Reference for Rebuild

## 1. Amplitude Charts API

**What we pull:** Chart data from saved charts by chart ID (used for activation metrics, funnels, retention, etc.).

- **Endpoint:** `GET {base_url}/chart/{chart_id}/query`
  - Base URL: `https://amplitude.com/api/3` (or configurable via `AMPLITUDE_BASE_URL`)
- **Auth:** Basic Auth — `Authorization: Basic {base64(api_key:secret_key)}`
- **Credentials:** `AMPLITUDE_API_KEY`, `AMPLITUDE_SECRET_KEY`
- **Response:** JSON with `isCsvResponse` flag; either `jsonResponse` (time series, funnels, segmentation) or `csvResponse` (CSV string)
- **Chart IDs:** Defined in `docs/metric-dictionary.yaml`; chart set (`core` + `supplemental`) drives which charts we query

---

## 2. Typeform API

**What we pull:** User feedback responses (open-ended answers, themes) for qualitative context in the report.

- **Responses:** `GET https://api.typeform.com/forms/{form_id}/responses`
  - Auth: `Authorization: Bearer {token}`
  - Query params: `page_size` (max 200), `since` (ISO 8601), `response_type=completed`, `after` (cursor for pagination)
- **Form metadata:** `GET https://api.typeform.com/forms/{form_id}` — used to map field IDs to question labels
- **Credentials:** `TYPEFORM_TOKEN`, `TYPEFORM_FORM_ID`
- **Lookback:** `LOOKBACK_DAYS` (default 7); if `since` causes 400, we retry without it and filter client-side

---

## 3. App Store (iTunes Lookup API)

**What we pull:** iOS app version, build, and release date for release context in the report.

- **Endpoint:** `GET https://itunes.apple.com/lookup?id={app_id}` (App ID `6480279827` hardcoded)
- **Auth:** None (public API)
- **Returns:** `results[0].version`, `results[0].build`, `currentVersionReleaseDate`, etc.
- **Release notes:** Merged with curated `docs/ios-release-notes.yaml` (version → highlights, summary, impact_tags). The Apple API does not return release notes text; we maintain that in YAML.

---

## 4. Slack Incoming Webhooks

**What we use:** Post the weekly digest to a Slack channel.

- **Method:** `POST` to webhook URL with JSON body
- **Auth:** The webhook URL itself is the credential; no separate header
- **Payload:** `{"text": "fallback", "blocks": [...], "channel": "#channel"}` — uses Blocks API (headers, sections, dividers, context)
- **Credentials:** `SLACK_WEBHOOK_URL`, optional `SLACK_CHANNEL` to override default

---

## Env Vars Summary

| Var | Purpose |
|-----|---------|
| `AMPLITUDE_API_KEY` | Amplitude API key |
| `AMPLITUDE_SECRET_KEY` | Amplitude secret key |
| `AMPLITUDE_BASE_URL` | Default `https://amplitude.com/api/3` |
| `TYPEFORM_TOKEN` | Typeform personal access token |
| `TYPEFORM_FORM_ID` | Target feedback form ID |
| `SLACK_WEBHOOK_URL` | Incoming webhook URL |
| `SLACK_CHANNEL` | Optional override for default channel |
| `LOOKBACK_DAYS` | Days of feedback to pull (default: 7) |

---

**Note:** The bot also uses `GEMINI_API_KEY` for AI analysis; that’s a separate concern from the data/notification APIs above.
