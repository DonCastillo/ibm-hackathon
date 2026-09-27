# format.md — Output format rules for Standup Sync

This file specifies length and style constraints for each of the three
output renderers (Slack, Email, Standup). These are hard constraints, not
suggestions — bake them directly into the LLM prompt used for each renderer
rather than relying on a generic "be concise" instruction, since
unconstrained LLM output tends to over-explain and drift wordy.

All three renderers consume the same summary object (see `architecture.md`
§6). Nothing here changes what data is available — only how much of it, and
in what shape, each format is allowed to surface.

## Two independent dimensions: format × audience

The app has two separate toggles that must not be conflated:

- **Format** — Slack / Email / Standup. Controls *structure and length*
  (bullets vs. paragraphs, how many lines, per-person vs. per-theme).
- **Audience/tone** — Developer / Client. Controls *vocabulary and framing*
  (technical terms vs. plain-English outcomes), independent of format.

Every format × audience combination must obey BOTH the format's length
rules below AND the audience rules in the "Audience/tone" section further
down. A Slack update for a client is still 3–6 bullets — it just doesn't
say "refactored the JWT middleware."

## Universal rule (applies to all three formats)

State **what changed**, not **why it matters** or **how it felt**. Do not
add interpretive commentary, narrative framing, or explanations of
significance. If a sentence answers "why should I care" rather than "what
happened," cut it.

Bad: "Refactored the authentication module to improve long-term
maintainability and reduce technical debt going forward."
Good: "Refactored auth module."

## 1. Slack renderer

- **Length: 3–6 bullet points total.**
- **Each bullet: one line, roughly 8–15 words.** No sub-bullets, no
  multi-sentence bullets.
- Must be scannable in under 10 seconds — if it requires scrolling on a
  mobile Slack client, it is too long. Cut content, don't shrink font.
- Tone: casual. Light emoji is acceptable (one per bullet max, not
  decorative strings of them).
- Blockers get their own bullet(s) with a warning indicator (e.g. a ⚠️ or
  "Blocker:" prefix), not folded into a theme bullet.
- **Wordiness signals to actively avoid:** full sentences with subordinate
  clauses ("...which allowed the team to..."), more than 6 bullets, any
  paragraph-style text.
- **Prompt constraint to enforce this:** explicitly instruct the model
  "Summarize in no more than 6 bullets, each under 15 words." Do not rely on
  "be concise" alone.

## 2. Email renderer

- **Length: 150–300 words total**, including subject line context.
- Structure: 2–4 short sections, one per theme/workstream (from the
  `groups` array in the summary object).
- **Each section is EITHER a short paragraph (2–3 sentences) OR 3–5
  bullets — never both.** Don't pad a section with both prose and a bullet
  list covering the same content.
- Tone: slightly more formal than Slack, but still plain language — no
  corporate filler ("leveraging synergies," "moving the needle").
- Blockers go in their own clearly labeled section (e.g. "Watch items" or
  "Blockers"), not scattered inside workstream sections.
- **Wordiness signals to actively avoid:** total length over ~400 words,
  any single section longer than a short paragraph, restating the same
  point in both a section intro and its bullets.
- **Prompt constraint to enforce this:** explicitly instruct the model
  "Write no more than 300 words total, organized into 2-4 sections of
  either a short paragraph or a bullet list, not both."

## 3. Standup renderer

- **Length: 2–4 lines per person, roughly 15–30 words per person total.**
- Format per person: "What I did" (1-3 short fragments, not full
  sentences) + "Blockers" (only if any exist for that person — omit the
  line entirely if none).
- The whole digest (all people combined) should be readable aloud in well
  under a minute.
- Tone: terse, fragment-style. Prefer "Refactored auth" over "I spent most
  of the day working on refactoring the authentication module."
- **Wordiness signals to actively avoid:** more than 3 bullets/fragments
  per person, explanatory sentences instead of terse fragments, restating
  what a teammate already covered.
- **Prompt constraint to enforce this:** explicitly instruct the model
  "For each person, write at most 3 short fragments (not full sentences)
  describing what they did, plus one blocker line only if applicable."

## Audience/tone: Developer vs. Client

This dimension is orthogonal to format (see above) — it changes vocabulary
and framing, not length or structure. Apply it as a second pass over
whichever format is selected.

### Developer audience
- Technical terms are fine and expected: file names, module/function names,
  library names, error types (e.g. "Fixed null pointer in `parseInvoice()`").
- Assumes familiarity with the codebase — no need to explain what a module
  does, just what changed in it.
- Blockers can be technical: "Blocked on flaky test in `payment_test.go`."

### Client audience
- **No file names, function names, module names, library names, or stack
  traces.** Translate technical changes into user-facing or business-facing
  outcomes.
- Frame around capability/impact, not implementation: not "refactored the
  JWT middleware" but "improved login reliability."
- Blockers become plain-English risk statements, not technical root causes:
  not "blocked on a flaky test in the CI pipeline" but "a quality check is
  taking longer than expected before this can ship."
- Still subject to the SAME length caps as the developer version of that
  format — client tone is not an excuse to add explanatory padding. If
  anything, translating jargon into plain English tends to run longer per
  idea, so trim elsewhere (fewer bullets/sections) to stay within the caps.
- Never expose internal terminology even in blocker/risk framing — a client
  should never see a class name, a repo name, or an error message.

### Translation examples (same underlying commit, both audiences)
| Developer phrasing | Client phrasing |
|---|---|
| "Refactored auth module, added rate limiting" | "Strengthened login security" |
| "Fixed race condition in payment webhook" | "Resolved an intermittent payment processing issue" |
| "Blocked on flaky test in CI" | "A pre-release quality check needs more time" |
| "Migrated DB schema for `orders` table" | "Improved backend performance for order processing" |

### Prompt constraint to enforce this
Pass the audience as an explicit parameter into the same prompt used for
format rendering, e.g.: "Write this for a [developer / non-technical
client] audience. [Developer: use technical terms like file/function names
freely.] [Client: translate all technical detail into plain-English
capability or outcome language — never mention file names, function names,
libraries, or error messages.]" Do this as one combined prompt (format +
audience), not two sequential passes — sequential passes risk the second
pass re-inflating length that the first pass already trimmed.

## Implementation notes for whoever builds the renderers (Bob or otherwise)

- Renderers are pure template/prompt functions: `render(summary_object) ->
  string`. They should not re-fetch data or re-run analysis — all content
  comes from the summary object already produced upstream.
- Put each renderer's prompt (if an LLM call is used per format, rather
  than pure string templating) in its own file under `prompts/`, named
  `prompts/slack.md`, `prompts/email.md`, `prompts/standup.md` — so the
  exact constraint text used is easy to point to for the hackathon
  submission's "how Bob was used" documentation.
- If a renderer's output violates its own length rule (e.g. Slack render
  comes back with 9 bullets), truncate or re-prompt rather than shipping
  the long version — don't silently let one format balloon past its limit
  in the demo.
- These limits are deliberately tight. If real output feels too sparse
  once implemented, loosen by no more than ~20% before concluding the rule
  is wrong — the default failure mode for LLM summarization is too long,
  not too short.
