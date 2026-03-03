R7 Spike: UX Acceptance Rubric for Shape B

## Context

Shape B currently fails `R7` in the fit check because "visually strong, simple, and intentional" is subjective and not yet measurable.

## Goal

Define a concrete acceptance rubric for `R7` and `R7.3` so we can judge pass/fail consistently during implementation and review.

## Questions & Answers

---

### X1-Q1: What objective layout checks define a successful 3-column desktop/laptop experience (column widths, hierarchy, scan path)?

**Column widths and proportions**

| Column | Width | Role | Collapsed state
|-----|-----|-----|-----
| Left (Sources) | `w-64` (256px fixed) | Inputs inventory: what data feeds the brief | Icon rail: 10x10 icon buttons per source, with panel-open button above a divider
| Center (Draft Workbench) | `flex-1` (fills remaining space, ~55-65% of viewport) | Primary workspace: the editable brief | Always visible, never collapses
| Right (Publish) | `w-[420px]` fixed | Output preview & publish action | Icon rail: Eye (preview) + Send (publish) buttons, with panel-open button above a divider


**Hierarchy checks (pass/fail)**

- Center column consumes the majority of viewport width at any common laptop resolution (1280px+). It must be the visually dominant region.
- Left and right columns are visually subordinate: smaller fixed widths, no competing headings at the same typographic scale as the brief title.
- The brief title (`text-2xl font-semibold`) is the single largest text element on screen. No other element competes.
- Section headings (`text-xs uppercase tracking-wider text-muted-foreground`) are clearly subordinate labels, not competing with content.
- Collapsed columns use `bg-secondary/30` tinting to differentiate from the main workbench background.


**Scan path**

The intended scan path is an **F-pattern** anchored by the center column:

1. **Header bar** (top-left) -- "Vector" logo + W48 identifier establishes context
2. **Brief title** (center, top) -- "Weekly Product Brief" is the first high-contrast element
3. **Sections flow vertically** downward in the center column (Executive Summary -> Key Metrics -> Hypotheses -> Recommendations)
4. **Left column** is a reference sidebar scanned when the user needs to inspect data provenance
5. **Right column** is an action destination scanned when the user is ready to publish


- No element in the left or right columns draws the eye before the brief title.
- Vertical section spacing (`space-y-10`) creates clear breathing room between content blocks to guide the downward scan.


---

### X1-Q2: What visual design constraints should be enforced for typography, spacing, contrast, and component density?

**Typography scale**

| Element | Class/Size | Font
|-----|-----|-----|-----
| App name (header) | `text-sm font-semibold` | Geist (sans)
| Brief title | `text-2xl font-semibold` | Geist (sans)
| Section headings | `text-xs font-medium uppercase tracking-wider` | Geist (sans)
| Body text (sections, hypotheses) | `text-base leading-relaxed` | Geist (sans)
| Evidence chips | `text-xs font-mono` | Geist Mono
| Meta text (dates, owners, stats) | `text-sm text-muted-foreground` | Geist (sans)
| Debugger / pipeline | `text-xs font-mono` | Geist Mono


**Constraints:**

- Maximum 2 font families: Geist (sans) and Geist Mono. No other fonts permitted.
- Body text minimum `text-base` (16px). Never smaller than 14px for readable content.
- `leading-relaxed` (line-height ~1.625) on all body/paragraph text.
- Monospace (`font-mono`) is reserved exclusively for: evidence chips, data values, pipeline debugger, and file references.


**Spacing**

- Content max-width constrained at `max-w-3xl` (768px) within the center column for comfortable reading line-length.
- Outer padding: `px-10 py-10` on the workbench content area.
- Section-to-section gap: `space-y-10` (40px). Distinct enough to visually separate topics.
- Intra-section gap (heading to content): `mb-4` (16px).
- No arbitrary pixel values (`p-[17px]`). All spacing uses the Tailwind scale.
- Gap classes preferred over margin; no `space-*` utility classes.


**Color & contrast**

The design uses a 5-color system defined in CSS custom properties (oklch):

| Token | Role | Light value
|-----|-----|-----|-----
| `--background` | Page bg | `oklch(0.975 0.003 80)` warm off-white
| `--foreground` | Primary text | `oklch(0.25 0.01 250)` deep slate
| `--muted-foreground` | Secondary text | `oklch(0.50 0.01 250)` mid-gray
| `--border` | Dividers & borders | `oklch(0.90 0.008 80)` light warm gray
| `--accent` | Hover states, chips | `oklch(0.94 0.012 170)` sage tint


- All colors use semantic design tokens (`text-foreground`, `bg-background`, etc.). No raw color values (`text-white`, `bg-black`) in application components.
- Confidence badges use background tinting at 15% opacity (`bg-emerald-500/15`) -- never full-saturation backgrounds.
- The Slack preview component is an exception: it uses hardcoded Slack brand colors (`#4a154b`, `#1d1c1d`, `#616061`, etc.) to faithfully represent the output.


**Component density**

- Source list items: one source per row, single-line primary info, secondary stats below. Hover reveals refresh. No more than 5-7 visible source rows without scrolling.
- Hypothesis cards: bordered cards with claim text + confidence badge. Data provenance is progressive-disclosure (collapsed by default).
- Recommendations: numbered list, one line per item with inline owner/eta metadata. No cards or borders needed.
- Evidence: small inline chips (not blocks), shown below section content. Click opens debugger.


---

### X1-Q3: What interaction standards define quality for the Sources, Draft, Report flow and Debugger entry/exit behavior?

**Sources panel interactions**

| Interaction | Expected behavior | Pass criteria
|-----|-----|-----|-----
| Expand Amplitude source | Chevron rotates 90deg, chart list reveals below | Transition is smooth (`transition-transform`), chart list indented under parent
| Refresh source | Spinner animation on icon, status dot pulses amber, resolves to green "synced" | Duration ~1.5s, button only visible on row hover, `stopPropagation` prevents parent click
| Stale warning | Amber text below source row | Only appears when `source.error` is truthy
| Collapse panel | Panel shrinks to icon rail showing source-type icons | Each icon has a `title` tooltip with source name + stat. Clicking any icon re-opens the panel


**Draft Workbench interactions**

| Interaction | Expected behavior | Pass criteria
|-----|-----|-----|-----
| Hover section | Pencil edit icon appears top-right | `opacity-0 group-hover:opacity-100` transition, no layout shift
| Click edit | Textarea replaces text, auto-focuses, auto-heights to content | `textareaRef.current.focus()` and dynamic `scrollHeight` sizing
| Save edit | Textarea replaced by updated text, section `content` state updated | Calls `onSectionUpdate(id, content)`, re-renders immediately
| Cancel edit | Reverts to original content, exits edit mode | Resets `draft` state to `section.content`
| Click evidence chip | Opens debugger drawer at bottom | Calls `onEvidenceClick(evidenceId)` which sets `debuggerOpen = true`
| Refresh draft | Spinner on button, "Regenerating..." label | 2.5s duration, button disabled during refresh
| Expand hypothesis data | "Data used" collapses/expands provenance block | Chevron rotation, indented bordered list with source details


**Publish panel interactions**

| Interaction | Expected behavior | Pass criteria
|-----|-----|-----|-----
| Default state | "Ready to publish" card with green dot, Publish + Preview buttons | No preview shown until user explicitly clicks Preview
| Click Preview | Slack Block Kit message renders with Mac window chrome | Shows full message with channel header, avatar, attachments
| Click Hide (preview) | Preview collapses back to ready-to-publish card | `EyeOff` icon button, returns to default state
| Click Publish | Button shows "Sending..." then "Sent to Slack" with checkmark | 1.2s delay, success state auto-resets after 3s
| Collapse panel | Icon rail: Eye + Send buttons with panel-open above divider | Eye button opens panel AND shows preview simultaneously


**Debugger drawer**

| Interaction | Expected behavior | Pass criteria
|-----|-----|-----|-----
| Open | Drawer appears from bottom, `shrink-0` in flex layout | Does not push or overlay content -- occupies footer slot at `h-52`
| Tab switch | Pipeline / Prompt toggle | Active tab has `bg-accent text-foreground`, inactive is ghost
| Pipeline step expand | Click reveals detail, output file, output preview | Indented below step row, bordered container
| Close | X button or re-toggle Debug bar button | Completely removed from DOM (`if (!open) return null`)


---

### X1-Q4: Which UX anti-patterns explicitly fail the quality bar?

**Hard fails -- any of these present means R7 is not met:**

1. **Clutter / information overload**

1. More than 2 levels of nesting visible by default (e.g., accordion inside accordion inside panel)
2. Evidence blocks expanded by default (they must be collapsed/progressive-disclosure)
3. Source chart lists expanded by default



2. **Ambiguous controls**

1. Buttons without visible labels AND without `title` tooltips in collapsed states
2. Icon-only buttons in the main content area (collapsed rails are exempt since they have tooltips)
3. Publish/Preview actions that are not clearly distinguishable from each other



3. **Weak hierarchy**

1. Side column text at the same size or weight as center column body text
2. Multiple `text-2xl` or larger headings competing on screen
3. Section headings using body-weight instead of the established `text-xs uppercase tracking-wider` pattern
4. Source panel items using `text-base font-bold` (they should be subordinate)



4. **Noisy chrome**

1. Scrollbars wider than 6px
2. Visible focus rings on non-interactive elements
3. Borders on every element (borders should only appear on: column dividers, section cards, input fields, debugger rows)
4. More than 5 distinct colors visible simultaneously (excluding the Slack preview which uses Slack's brand palette)



5. **Layout violations**

1. Content not constrained to `max-w-3xl` in the center column (causes overly long line lengths)
2. Side panels wider than the center content area
3. Horizontal scrolling at any viewport width >= 1280px
4. Fixed positioning or floats used for layout (flex only)



6. **Interaction hazards**

1. Edit mode without a visible Cancel action
2. Destructive actions (Publish) without clear state feedback
3. Collapsed panel icons that don't provide any way to re-expand the panel
4. Modals or overlays that block the brief (the debugger drawer is the only acceptable overlay pattern, and it doesn't overlay -- it pushes)





---

### X1-Q5: Which reference UX examples should anchor the bar, and which traits are in-scope to emulate versus out-of-scope?

**Primary references**

| Reference | Traits to emulate (in-scope) | Traits out-of-scope
|-----|-----|-----|-----
| **Google NotebookLM** | Collapsible side panels with icon rails when collapsed; subtle background tinting on side columns (`bg-secondary/30`); clean document-centric center; thin scrollbars | Audio overview feature; multi-notebook navigation; AI chat panel
| **Linear** | Minimal chrome; dense-but-readable list views; progressive disclosure; keyboard-first patterns; font pairing (sans headings + mono for IDs) | Drag-and-drop boards; multi-select bulk actions; custom views/filters
| **Notion** | Content-first layout with max-width constraints; inline editing (click-to-edit sections); clean typography hierarchy; evidence as inline tags/chips | Database views; slash commands; page tree navigation; template system
| **Slack Block Kit Builder** | Faithful Slack message preview with Mac window chrome; attachment left-bar visual language; APP badge + timestamp rendering | Block Kit JSON editor; real-time API integration; interactive message actions


**Specific traits anchoring the bar:**

- **NotebookLM's collapsed-panel pattern**: When a panel is collapsed, it becomes an icon rail with tooltips, not completely hidden. This preserves context awareness.
- **Linear's information density**: Source list shows name + type icon + status dot + stat in a single row. No wasted vertical space, but not cramped.
- **Notion's document editing**: Click-to-edit with a ghost pencil icon on hover. No "enter edit mode" button that adds UI before you need it.
- **Slack Block Kit's preview fidelity**: The publish preview must look like a real Slack message (purple avatar, APP badge, attachment bars, Slack typography), not an abstract representation.


---

### X1-Q6: What review checklist should be run before calling R7 satisfied in the shaping fit check?

**R7 Review Checklist**

Run at viewport sizes: 1280x800 (laptop), 1440x900 (common), 1920x1080 (desktop).

**Layout (5 checks)**

- Center column occupies visual majority (>50% of viewport width) at all tested resolutions
- Left column is exactly `w-64` (256px) when open; collapses to icon rail (~48px)
- Right column is exactly `w-[420px]` when open; collapses to icon rail (~48px)
- Center content constrained to `max-w-3xl` with `px-10` padding
- No horizontal scrolling at any tested resolution


**Typography (4 checks)**

- Brief title is the single largest text on screen (`text-2xl`)
- Only 2 font families in use (Geist sans + Geist Mono)
- Body text is minimum `text-base` (16px) with `leading-relaxed`
- Section headings are consistently `text-xs uppercase tracking-wider text-muted-foreground`


**Visual design (5 checks)**

- All component colors use semantic tokens (no raw `text-white`, `bg-gray-*`, etc.)
- Maximum 5 colors visible in the app chrome (excluding Slack preview)
- Confidence badges use translucent tinting, not saturated backgrounds
- Collapsed columns have visible `bg-secondary/30` tinting
- Scrollbars are thin (6px) with transparent tracks


**Interactions (7 checks)**

- Every collapsed panel icon has a `title` tooltip describing its function
- Each collapsed panel has a panel-open button (with divider separator) above the action icons
- Section hover reveals edit icon; clicking enters inline edit mode with autofocus
- Edit mode shows both Save and Cancel actions
- Publish button shows clear state progression: default -> "Sending..." -> "Sent to Slack" (with auto-reset)
- Evidence chips in the draft are clickable and open the debugger drawer
- Debugger drawer opens/closes without overlaying or shifting the brief content


**Anti-pattern audit (4 checks)**

- No more than 1 level of nesting visible by default
- No icon-only buttons in content areas without tooltips
- No competing headings at the same typographic scale
- No modals, toasts, or overlays blocking the brief


---

## Acceptance

Spike is complete. The rubric above provides:

- **25 measurable pass/fail checks** organized into Layout, Typography, Visual Design, Interactions, and Anti-pattern categories
- **Explicit anti-pattern fail list** (Q4) that any reviewer can apply without subjective judgment
- **Reference anchors** (Q5) with specific traits scoped in/out so the bar is clear but not unbounded
- **Interaction truth table** (Q3) mapping every user action to expected behavior


To satisfy R7/R7.3, all 25 checklist items must pass. Any single item from the anti-pattern list (Q4) being present is an automatic fail.