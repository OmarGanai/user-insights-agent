# Metric Dictionary

Canonical source for chart mapping is `/Users/omarganai/Coding/amplitude-insights-bot/docs/metric-dictionary.yaml`.

## Global Standards

- `app_id`: `639837` (`tenant-prod` only)
- Segment lock: `userdata_cohort is not 5cn1caqx` (exclude tenant employees)
- Time settings: `Last 4 Weeks`, `Weekly`, `Previous Period vs`, `excludeCurrentInterval=false`
- Implementation note: with `excludeCurrentInterval=false`, API responses commonly include 5 weekly buckets with the latest bucket marked incomplete.
- Chart type standard: `funnel`, `retention`, `events_segmentation`

## Glossary

- `DENT`: Domain-specific action family for high-value creation actions.
- `Hive`: Shared collaboration space feature.
- `Life Tab`: Product surface where day-to-day personal activity happens.

## Chart Sets

### `legacy` (default)

| Group | Metric Key | Chart Name | Chart Type | Chart ID | Status | Intent | Reuse / Alias |
|---|---|---|---|---|---|---|---|
| core | `legacy_signup_to_life_tab_viewed` | Signup Completed -> Life Tab Viewed | `funnel` | `oys29da5` | validated | Legacy top-of-funnel engagement proxy | - |
| core | `legacy_signup_to_task_created` | Signup Completed -> Task Created | `funnel` | `rviqohkp` | validated | Legacy activation proxy through task creation | - |
| core | `legacy_signup_to_event_created` | Signup Completed -> Event Created | `funnel` | `hc4183lh` | validated | Legacy activation proxy through event creation | - |
| core | `legacy_signup_to_note_created` | Signup Completed -> Note Created | `funnel` | `p9fsuwzc` | validated | Legacy activation proxy through note creation | - |
| core | `legacy_signup_to_appliance_added` | Signup Completed -> House: Appliance Added | `funnel` | `w2p98xci` | validated | Legacy household setup completion proxy | Reused in `activation_v1` |
| supplemental | `legacy_signup_to_life_tab_member_tapped` | Signup Completed -> Life Tab Member Tapped | `funnel` | `gfhad295` | validated | Legacy collaboration intent diagnostic | - |
| supplemental | `legacy_hive_member_invited_retention` | Hive Member Invited Retention | `retention` | `sb8w2oof` | validated | Legacy repeat invite behavior diagnostic | - |
| supplemental | `legacy_signup_to_task_created_diagnostic` | Signup Completed -> Task Created (Diagnostic) | `funnel` | `rviqohkp` | validated | Appendix stability in legacy mode | Alias of `legacy_signup_to_task_created` |

### `activation_v1` (cutover target)

| Group | Metric Key | Chart Name | Chart Type | Chart ID | Status | Intent | Reuse / Alias |
|---|---|---|---|---|---|---|---|
| core | `core_composite_activation_14d` | Activation KPI: Signup Completed -> Any High-Value Action | `funnel` | `0pl4jd50` | validated | Primary activation KPI against 40-50% target | - |
| core | `core_signup_to_any_dent_created` | Signup Completed -> Any DENT Created | `funnel` | `i3i58uut` | validated | Creation behavior coverage diagnostic | - |
| core | `core_signup_to_calendar_connect_completed` | Signup Completed -> Calendar Connect: Completed | `funnel` | `ectuc1bm` | validated | Calendar setup completion path | - |
| core | `core_signup_to_appliance_added` | Signup Completed -> House: Appliance Added | `funnel` | `w2p98xci` | validated | Household setup activation path | Alias of `legacy_signup_to_appliance_added` |
| core | `core_signup_to_hive_member_invited` | Signup Completed -> Hive: Member Invited | `funnel` | `p8g2bhzg` | validated | Collaboration activation path | - |
| supplemental | `supp_dent_action_mix_breakdown` | DENT Action Mix Breakdown | `events_segmentation` | `9wo48n2l` | validated | Action-level DENT mix with signup-denominator conversion context | - |
| supplemental | `supp_calendar_started_to_completed` | Calendar Started -> Completed | `funnel` | `i2cqwsyx` | validated | Calendar connection quality diagnostics | - |
| supplemental | `supp_14d_repeat_after_activation_proxy` | Repeat Behavior After Activation Proxy | `retention` | `0zug54x7` | validated | Post-activation repeat behavior signal | - |

## Cutover Rule

- All `activation_v1` chart IDs are now present and `validated`.
- Default `REPORT_CHART_SET=activation_v1`; use `legacy` only for rollback.
