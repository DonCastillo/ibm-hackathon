# UI.md — Making Standup Sync presentable

Goal: a site that feels like **VS Code with the Monokai theme**, with a SaaS-style landing page at `/` and the app at `/standup`. No framework and no build step, consistent with the rest of the project: plain HTML, CSS and JS.

## 1. Design system

**Colors (Monokai), as CSS variables in `theme.css`:**

| Token | Hex | Used for |
|---|---|---|
| `--bg` | `#272822` | Editor background |
| `--bg-panel` | `#1e1f1c` | Sidebars, panels, inputs |
| `--bg-raised` | `#3e3d32` | Cards, hover, borders |
| `--text` | `#f8f8f2` | Body text |
| `--muted` | `#75715e` | Comments, hints, line numbers |
| `--pink` | `#f92672` | Primary action, errors, keywords |
| `--green` | `#a6e22e` | Success, done steps, highlights |
| `--yellow` | `#e6db74` | Strings, commit hashes, selected pills |
| `--orange` | `#fd971f` | Warnings, gradients |
| `--purple` | `#ae81ff` | Branches, numbers, status bar |
| `--cyan` | `#66d9ef` | Links, focus rings, active step |

- **Fonts:** system UI font for interface text (as VS Code does). **JetBrains Mono** (Google Fonts) for headings, code, logs and outputs.
- **Icons:** VS Code's own **Codicons** (`@vscode/codicons` from jsdelivr), so icons match the editor exactly.
- **Motion:** subtle only (hover lifts, pulsing active step, flowing workflow line). All animation is turned off under `prefers-reduced-motion`.
- **Accessibility:** text contrast ≥ 4.5:1 on `--bg`, visible cyan focus rings, keyboard-reachable controls, and `aria-live` on status and progress updates.

## 2. Editor chrome (shared by both pages)

```
┌ ● ● ●        Standup Sync — Visual Studio Code        ⌘K Search ┐  title bar
├──┬──────────────────────────────────────────────────────────────┤
│⚡│ README.md ×  │ standup.sync │                                 │  editor tabs
│⎇ │──────────────────────────────────────────────────────────────│
│▶ │  1 │                                                         │
│? │  2 │   page content (editor area, faint line-number gutter)  │
│  │  3 │                                                         │
├──┴──────────────────────────────────────────────────────────────┤
│ ⎇ main  ✓ 0 problems        Monokai   Claude Haiku 4.5   UTF-8   │  status bar (purple)
└─────────────────────────────────────────────────────────────────┘
```

- **Title bar:** macOS window dots, centered title, and a fake command-palette box that opens a small menu (Home, Sync My Standup, How it works).
- **Activity bar** (left icon rail): Home (`/`), Run ▶ (`/standup`), How it works (anchor), GitHub repo link. The current page is highlighted with the VS Code left accent bar.
- **Editor tabs:** the landing page is `README.md`, and the app is `standup.sync`. Clicking a tab navigates between pages.
- **Status bar:** branch icon, a problem count (turns pink on error), the theme name, and the LLM model name.
- **Mobile (<720 px):** the activity bar becomes a bottom icon row, the title bar shrinks to the dots and the title, and tabs scroll horizontally. No horizontal page scroll.

## 3. Landing page (`/`, tab `README.md`)

1. **Hero**
   - **Logo:** an inline SVG of a lightning bolt inside code braces, `{⚡}`, in the pink-to-orange gradient. Also used as the favicon.
   - **Title** "Standup Sync" in JetBrains Mono, with a blinking cursor.
   - **Tagline:** "Turn your git history into standup notes, Slack updates and email digests, written from the actual code changes."
   - **Buttons:** a primary **⚡ Sync My Standup** (goes to `/standup`) and a secondary **See how it works** (scrolls to the workflow).
   - **Hero visual:** a mini editor split. On the left, raw `git log` lines in Monokai colors (hash yellow, branch purple, author green). On the right, the Slack bullets they become. The left side "types in" and the right fades in (CSS only).
2. **Features** (6 cards in a 3×2 grid, 1 column on mobile). Each card has a Codicon in an accent color, a title and one sentence:
   - **Reads the code, not the commit message.** Summaries come from diffs, so "fix stuff" still becomes a real update.
   - **Accomplishments only.** Formatting, spacing, reverts and minor tweaks are filtered out automatically.
   - **Every branch.** Unmerged feature-branch work is included, so nothing is missed.
   - **3 formats × 2 audiences.** Slack, Email and Standup, for developers or clients, all generated at once.
   - **Private repos.** Works with a Personal Access Token, which is never stored.
   - **Who shipped what.** Per-developer highlights and branches at a glance.
3. **Why it's different:** a compact comparison styled like a VS Code diff view. Red `-` lines are "Changelog bots: list commit messages as-is". Green `+` lines are "Standup Sync: reads diffs, filters noise, writes for your audience".
4. **How it works** (workflow graphic): five nodes joined by an animated dashed line, with a "no LLM" or "LLM" badge on each so visitors see where the AI is used. Built in HTML and CSS; it goes vertical on mobile.
   `Git repo (all branches)` → `Noise filter: merges, lock files, spacing, reverts` → `LLM reads diffs: summary + MAJOR/MINOR` → `Highlights: major updates only` → `Outputs: Slack · Email · Standup × Developer · Client`
   The copy matches `plan/filtering.md`.
5. **Call to action:** a VS Code terminal panel, a short pitch.
   ```
   $ standup-sync --repo your-org/app --since "7 days ago"
   ✓ 27 commits → 6 highlights · 3 formats · 2 audiences
   ```
   Below it: "Stop rebuilding your week from `git log`." and a large **⚡ Sync My Standup** button.
6. **Footer:** the status bar, plus a small "Built with IBM Bob for the IBM Bob 2.0 Hackathon" line.

## 4. App page (`/standup`, tab `standup.sync`)

**Layout:** on desktop, a two-column editor split. The form is on the left (sticky) and the results are on the right. On mobile, they stack.

**Form**, styled like the VS Code Settings UI:
- Labels in small caps and muted color, with the `?` tooltips restyled as dark hover cards.
- Inputs use the dark panel background, with a cyan border and glow on focus. Date inputs use `color-scheme: dark`.
- The date presets become chip toggles: the selected chip is yellow with dark text.
- A field-level error adds a pink border and a pink message under the field.

**⚡ Sync My Standup button:** full width with a pink-to-orange gradient and bold text.
- **Enabled:** a slow glow pulse and a keyboard hint (`⌘↵` / `Ctrl+↵`).
- **Disabled:** grey, with a hint under it that names what's missing ("Add a repository and pick a date range").
- **Running:** it shows a spinner and "Syncing…".

**Progress tracker:** a horizontal 5-step stepper (vertical on mobile), reusing the existing `step-*` ids.
- The steps: Clone → Extract → Filter → Analyse (LLM) → Write outputs.
- **Pending:** grey circle. **Active:** cyan ring with a spinning arc. **Done:** green circle with a check.
- Under the stepper, an **OUTPUT panel** styled like VS Code's shows each progress message as a timestamped log line, with the elapsed time.

**Spinner:** a Codicon `sync~spin`-style ring in cyan and pink, used in the button and the active step. The results area shows **skeleton placeholders** (shimmering bars) for Output Formats while the LLM works.

**Errors:**
- An inline banner in the results area, styled like a VS Code notification: pink left border, error icon, a one-line title, the message, and action buttons ("Add a token" focuses the token field; "Try again" re-runs).
- A toast in the bottom-right corner that fades out after 6 seconds.
- The status bar shows "1 problem" in pink.

**Results:**
- **Report title:** "Accomplishments between …", with the period in the yellow string color.
- **Output Formats:** Slack / Email / Standup look like editor tabs. Developer / Client is a segmented toggle. The content sits in a monospace editor pane with a line-number gutter and light syntax coloring (bullets pink, `*bold*` yellow, headings cyan). Copy is an icon button with a "Copied!" toast.
- **Developer Stats:** a dark table. Highlights in green, commits in purple, branches as small purple tags.
- **Raw git log:** a terminal-style panel, collapsed to 12 lines with "Show all". Hash yellow, `[branch]` purple, author green.

## 5. Files

| File | Change |
|---|---|
| `frontend/landing.html` | New landing page |
| `frontend/standup.html` | The current `index.html`, moved and restyled; existing element ids kept |
| `frontend/theme.css` | New: tokens, fonts, editor chrome, shared components (buttons, cards, panels, toasts) |
| `frontend/landing.css`, `frontend/standup.css` | Page-specific styles (`standup.css` replaces `styles.css`) |
| `frontend/app.js` | Small additions: stepper states and elapsed time, error banner and toast (extending `_setStatus`), disabled-button hint, `⌘↵` shortcut, raw log coloring and collapse |
| `frontend/logo.svg` | New logo and favicon |
| `backend/main.py` | `/` serves `landing.html`; new `/standup` route serves `standup.html` |

Reuse existing logic unchanged: `_setStatus`, `_reportTitle`, `_applyFormats`, `renderDevStats` / `_renderDevRows`, `copyTab`, `_updateGenerateBtn`, and the SSE handling in the generate handler (`frontend/app.js`).

## 6. Phases (in priority order for the deadline)

1. **Theme and app page** (demo-critical): `theme.css`, the chrome, the `/standup` restyle, button, stepper, spinner, errors, skeletons. About 3 h.
2. **Landing page:** hero, features, differentiation, workflow graphic, CTA, logo. About 2–3 h.
3. **Polish:** mobile pass, reduced motion, keyboard shortcut, toasts, command-palette menu. About 1 h.

Each phase leaves the app working, so it can stop after any phase.

## 7. Done when

- `/` and `/standup` both look like VS Code with Monokai, on a laptop and at 375 px wide.
- On `/standup`, every state looks deliberate: idle (disabled with a hint), running (stepper plus skeletons), error (banner plus toast), and success.
- The landing page's feature and workflow copy matches what the app actually does (`plan/filtering.md`).
- Screenshots of both pages are usable for the cover image and slides (`tasks.md` §6).
