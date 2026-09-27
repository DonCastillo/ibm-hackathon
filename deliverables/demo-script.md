# Demo video script — Standup Sync

**Target length:** about 3:00 total: **slides 1:30** plus **live demo 1:30**.
**Order:** slides 1–4 → slide 5 leads into the **live demo** → slides 6–10.
**Pace:** about 150 words a minute. Each slide's word count and time is listed, so you can see where to trim if you run long.

---

## Before you hit record

- **Wake the server:** open https://standup-sync.onrender.com a minute or two early. The free plan sleeps when idle, and the first visit takes about 30 seconds.
- **Rehearse the demo run once** with the same repo and range you'll record. `https://github.com/directus/directus` with **48h** worked well: a real open-source repo with feature branches, finished in about 15 seconds.
- **Have two tabs ready:** the slides in presenter mode, and `/standup` in a browser window at the same size.
- **Leave the repo field empty,** so the audience sees you paste the URL.

---

## Slide 1 — Standup Sync (cover)
**~9 s · 23 words**

> Hi, I'm Don. This is Standup Sync: it writes your standup, Slack update and client email from the code itself, not commit messages.

---

## Slide 2 — Every update starts with git log
**~9 s · 25 words**

> A typical week in git log: "fix stuff", "wip", a revert. None of it says what got done, so developers dig through diffs by hand.

---

## Slide 3 — Slow, error-prone, repeated
**~9 s · 19 words**

> It's slow, it's error-prone, with unmerged work forgotten and reverts counted as progress, and it's repeated for every audience.

---

## Slide 4 — One click, six ready-to-post updates
**~9 s · 21 words**

> Standup Sync makes it one click: paste a repo, pick a range, press sync. Six updates, for developers and for clients.

---

## Slide 5 — Feels like your editor → LIVE DEMO
**Intro ~3 s · 10 words, then the demo ~90 s · 121 words, spoken while you click**

*On slide 5, one line, then switch to the browser:*

> It's built to feel like VS Code. Let's try it.

| Time | On screen | Say |
|---|---|---|
| 0:00 | `/standup`, empty form | "Here's the app. I'll use a real open-source repo, Directus." |
| 0:05 | Paste `https://github.com/directus/directus` | "Any git host works, and private repos just need a token." |
| 0:12 | Click **48h**, point at the button's hint and ⌘↵ | "Pick the last 48 hours, and press Sync My Standup." |
| 0:18 | Click **⚡ Sync My Standup**; the tracker starts | "Every step runs live. It clones every branch, not just main." |
| 0:28 | Raw git log appears (scroll to it briefly) | "Within seconds, here's every commit, tagged with its branch. That's the raw material." |
| 0:40 | **Analyse (LLM)** step is active | "Now the model reads the actual diffs, not the messages, and keeps only the major changes." |
| 0:52 | Results appear, **Slack** tab | "Here's the Slack update: short bullets written from the code, with file names for developers." |
| 1:02 | Click **Clients** | "One click, and it's rewritten for a client, in plain English." |
| 1:10 | Click **Email**, then **Standup** | "The same week as an email, and as per-person standup notes." |
| 1:18 | Scroll to **Developer Stats** | "And who shipped what, on which branch, including unmerged work." |
| 1:25 | Click **Copy**; the toast appears | "Copy, paste, done." |

*If the run takes longer than expected, keep talking over the progress tracker. The OUTPUT log gives you something to point at.*

---

## Slide 6 — Five steps, only two use AI
**~10 s · 24 words**

> Five steps, only two use AI. Plain code filters the noise first, so the model only sees what matters, and a run costs cents.

---

## Slide 7 — Not another changelog bot
**~8 s · 17 words**

> Unlike changelog bots, we read diffs, report accomplishments only, cover every branch, and write for your audience.

---

## Slide 8 — Three Bob sessions, one working app
**~13 s · 30 words**

> IBM Bob built the first version in three sessions: it planned from our docs, set up watsonx.ai from IBM's documentation, then used a subagent and Agent mode to build features.

---

## Slide 9 — Tested on real repositories
**~9 s · 22 words**

> It holds up: a hundred and two tests, eight bugs fixed, and VS Code's repo went from thirteen minutes to under three.

---

## Slide 10 — Stop rebuilding your week from git log
**~5 s · 12 words**

> Stop rebuilding your week from git log. Try Standup Sync today. Thanks!

---

## Timing summary

| Part | Time | Words |
|---|---|---|
| Slides 1–10 (including slide 5's one-line intro) | ~1:30 | 203 |
| Live demo | ~1:30 | 121 |
| **Total** | **~3:00** | 324 |

**If you need to cut time:**
- **Slides:** merge slides 2 and 3 into one line: "Commit messages don't say what got done, so updates are slow, error-prone and rewritten for every audience."
- **Demo:** skip the Standup tab, or the scroll to the raw git log.
