Code Cannon: Detect setup state, guide first-time configuration, populate labels, and walk through optional config values

---

## Detect state

Before taking any action, determine which state the project is in. Run these checks in order.

**Check A — Is this the Code Cannon skill library repo itself?**

```bash
test -f sync.sh && test -d skills
```

If both exist at the working directory root → **go to State 1**.

**Check B — Is there any Code Cannon submodule presence?**

```bash
test -d CodeCannon
```

```bash
test -f .gitmodules && grep -q CodeCannon .gitmodules
```

If either is true → **go to State 2**.

**Check C — State 1 fallback**

If `.codecannon.yaml` is absent AND neither `CodeCannon/` nor `.gitmodules` exist → **go to State 1**.

Otherwise → **go to State 2**.

---

## State 1 — Just checking it out

Do not configure anything. Do not touch any file.

Tell the user warmly that Code Cannon is designed to live as a submodule inside another project — running `/setup` here in the Code Cannon repo itself isn't the intended path.

Offer two forward paths and ask which they want:

**Path A — "I want to understand how Code Cannon works"**

Explain the three-layer model:
- **Skills** (`skills/*.md`) — portable workflow instructions with `main`-style tokens for project-specific values (see `config.schema.yaml`)
- **Config** (`.codecannon.yaml`) — a project's values that fill those tokens at sync time
- **Sync** (`sync.sh`) — reads the config, substitutes values, and writes generated command files for each adapter (Claude Code → `.claude/commands/`, Cursor → `.cursor/rules/`)

List the available skills:

| Skill | What it does |
|---|---|
| `/start` | Creates a GitHub issue, feature branch, and writes code |
| `/submit-for-review` | Checks, commits, opens PR, spawns review agent, merges |
| `/review` | Standalone code review on any PR |
| `/deploy` | Bumps version, creates GitHub Release, promotes to production |
| `/status` | Snapshot of open PRs and issues for the team |
| `/setup` | This skill — configures Code Cannon in a project |

Point to README.md for full documentation. Do not touch any file.

**Path B — "I want to add Code Cannon to my project"**

Show the exact command sequence:

```bash
cd /path/to/your-project
git submodule add https://github.com/LightbridgeLab/CodeCannon.git CodeCannon
git submodule update --init
cp CodeCannon/templates/codecannon.yaml .codecannon.yaml
# Edit .codecannon.yaml — set branch names, commands, adapters
CodeCannon/sync.sh
```

Do not touch any file. The user runs these commands in their project directory.

---

## State 2 — Partial or broken setup

Run checks 1–7 in order. Stop at the first failing check and address it. After describing the fix, tell the user to run `/setup` again once they've resolved it. Do not continue past a failing check.

### Check 1 — CodeCannon/sync.sh present

```bash
test -f CodeCannon/sync.sh
```

If missing: the submodule was added to `.gitmodules` or `CodeCannon/` exists as an empty directory, but it hasn't been initialized. Show:

```bash
git submodule update --init --recursive
```

Offer to run it. If the user agrees, run it. If they decline, tell them to run it manually before continuing. Stop.

### Check 2 — gh installed

```bash
which gh
```

If not found: "`gh` is required by all Code Cannon skills. Install it with `brew install gh` (macOS) or from https://cli.github.com." Cannot proceed without it. Stop.

### Check 3 — gh authenticated

```bash
gh auth status
```

If exit code is non-zero: "You're not authenticated with GitHub." Show:

```bash
gh auth login
```

Cannot proceed without it. Stop.

### Check 4 — Inside a GitHub repository

```bash
gh repo view --json name
```

If exit code is non-zero: warn that most skills require a GitHub remote. Skills can be read and configured, but `/start`, `/submit-for-review`, `/review`, `/deploy`, and `/status` will fail without one. This is not a hard stop — ask if the user wants to continue configuring anyway.

### Check 5 — .codecannon.yaml present

```bash
test -f .codecannon.yaml
```

If missing: "I'll create `.codecannon.yaml` from the template — you'll want to review the branch names and commands before running sync."

Show:

```bash
cp CodeCannon/templates/codecannon.yaml .codecannon.yaml
```

Ask permission to run it. If the user agrees, run it. If they decline, tell them to run it manually.

After creating the file, proceed immediately to Check 5b.

### Check 5b — Profile selection (only on first setup)

This check runs only when Check 5 just created `.codecannon.yaml` from the template. If `.codecannon.yaml` already existed before this `/setup` invocation, skip to Check 6.

Ask the user:

> "What level of process does this project need?"
>
> **1. Lightweight** — Fast iteration. AI review is advisory, features merge to main, no QA workflow.
>
> **2. Standard** — Integration branch with AI-gated review. QA and milestones available but not required.
>
> **3. Governed** — Full traceability. QA handoff, assigned reviewers, milestones, structured labels.
>
> **4. Custom** — Configure each setting individually.
>
> Pick a number, or describe your workflow and I'll recommend one.

Wait for response. If the user describes their situation instead of picking a number, recommend the best-fit profile and confirm before applying.

**Apply profile values to `.codecannon.yaml`:**

After the user selects a profile, ask follow-up questions and write values. Show every change before writing and ask "Apply these values to `.codecannon.yaml`? (yes/no)". Write only on yes.

**Lightweight:**
- "What's your production branch name?" (default: `main`)
- Write: `BRANCH_PROD: <answer>`, `REVIEW_GATE: "advisory"`. Leave `BRANCH_DEV`, `BRANCH_TEST`, `DEFAULT_REVIEWERS`, `TICKET_LABELS`, and all QA labels commented out.
- No further questions. Say: "Lightweight profile applied. Check the workflow commands (`CHECK_CMD`, deploy commands, etc.) and run `/setup` again to finish configuration." Stop.

**Standard:**
- "What's your production branch name?" (default: `main`)
- "What's your integration branch name?" (default: `development`)
- Write: `BRANCH_PROD: <answer>`, `BRANCH_DEV: <answer>`, `REVIEW_GATE: "ai"`. Leave `BRANCH_TEST` and QA labels commented out.
- Say: "Standard profile applied. Check the workflow commands and run `/setup` again to finish configuration." Stop.

**Governed:**
- "What's your production branch name?" (default: `main`)
- "What's your integration branch name?" (default: `development`)
- "Do you need a separate test/staging branch between integration and production? (yes/no)"
  - If yes: "What's the test/staging branch name?" (default: `staging`)
  - Write `BRANCH_TEST: <answer>`.
- Write: `BRANCH_PROD: <answer>`, `BRANCH_DEV: <answer>`, `REVIEW_GATE: "ai"`, `QA_READY_LABEL: "ready-for-qa"`, `QA_PASSED_LABEL: "qa-passed"`, `QA_FAILED_LABEL: "qa-failed"`.
- Say: "Governed profile applied. Check the workflow commands and run `/setup` again to finish configuration." Stop.

**Custom:**
- Say: "Open `.codecannon.yaml` and check the values marked with comments — especially `BRANCH_PROD`, `BRANCH_DEV`, `REVIEW_GATE`, `CHECK_CMD`, and the deploy commands. Then run `/setup` again." Stop.

### Check 6 — .codecannon.yaml stale values

Read `.codecannon.yaml`. Apply the following checks conservatively — only flag a value if you are confident it points to something that does not exist:

- If `VERSION_READ_CMD` references `package.json` and no `package.json` exists at the project root → flag it
- If `BRANCH_DEV` is set to a non-empty value and that branch does not appear in `git branch -a` → flag it
- If `BRANCH_TEST` is set to a non-empty value and that branch does not appear in `git branch -a` → flag it

If nothing is confidently broken, do not flag anything. When in doubt, do not flag.

If anything is flagged: show the specific key names and what they should likely be changed to. Do not modify the file. Tell the user to update these values and run `/setup` again. Stop.

### Check 7 — Generated skill output present

Check whether sync.sh has been run by looking for any of the adapter output directories configured in `.codecannon.yaml`:

```bash
test -d .claude/commands || test -d .cursor/rules || test -d .agents/skills || test -d .gemini/skills
```

If none exist: "sync.sh hasn't been run yet — the skill commands don't exist."

Show:

```bash
CodeCannon/sync.sh
```

Ask permission to run it. If the user agrees, run it. If they decline, tell them to run it manually before continuing. Stop.

---

## State 3 — Everything configured

All checks pass. Run phases 1–4 in order.

---

### Phase 1 — Health summary

Print one sentence confirming the setup looks healthy. Read `.codecannon.yaml` and infer the workflow profile for display:

- `REVIEW_GATE` is `"advisory"` or `"off"` AND `BRANCH_DEV` is empty → **Lightweight**
- `REVIEW_GATE` is `"ai"` AND `BRANCH_DEV` is set AND `QA_READY_LABEL` is empty → **Standard**
- `REVIEW_GATE` is `"ai"` AND `QA_READY_LABEL` is set → **Governed**
- Anything else → **Custom**

Check whether the configured dev/test branches exist in the remote (skip checks for empty values):

```bash
git branch -a | grep -q "remotes/origin/<BRANCH_DEV value>"
git branch -a | grep -q "remotes/origin/<BRANCH_TEST value>"
```

Display:

```
Setup looks healthy. Profile: <inferred profile>

  BRANCH_PROD:         <value>
  BRANCH_DEV:          <value>  (exists in remote: yes/no/not set)
  BRANCH_TEST:         <value>  (exists in remote: yes/no/not set)
  REVIEW_GATE:         <value>
  CHECK_CMD:           <value>
  MERGE_CMD:           <value>
  Adapters:            <list from config>

  Optional config:
    DEFAULT_MILESTONE              — set / unset
    DEFAULT_REVIEWERS              — set / unset
    TICKET_LABELS                  — set (N labels) / unset
    TICKET_LABEL_CREATION_ALLOWED  — set / unset
    QA_READY_LABEL                 — set / unset
    PLATFORM_COMPLIANCE_NOTES      — set / unset
    CONVENTIONS_NOTES              — set / unset
```

A value counts as "set" if it is present, uncommented, and non-empty in `.codecannon.yaml`.

---

### Phase 2 — Label population

Run:

```bash
gh label list --limit 100 --json name,color,description
```

If zero labels are found, treat this as a greenfield repository and offer a starter label baseline before asking about `TICKET_LABELS`.

Show this recommendation:

```
No labels were found. For new projects, a practical baseline is:
  - bug
  - enhancement
  - chore
  - documentation
  - ready-for-qa
  - qa-passed
  - qa-failed
```

Ask: **"Create any missing labels from this baseline now? (yes/no)"**

Wait for response.

- **yes** → create missing labels only (do not recreate existing labels). Use sensible colors and short descriptions.
- **no / skip / anything else** → continue without creating labels.

After this step (or if labels were non-zero initially), run `gh label list --limit 100 --json name,color,description` again and continue with the numbered list flow below.

Display the results as a numbered list:

```
Available labels (N found):
  1. bug — Something isn't working
  2. enhancement — New feature or request
  3. good first issue — Good for newcomers
  ...
```

Ask: **"Write these label names to `.codecannon.yaml` as TICKET_LABELS? (yes / no / list specific numbers)"**

Wait for the user's response.

- **yes** → use all labels
- **numbers** (e.g. `1,3,5`) → use only those labels
- **no / skip / anything else** → skip this phase, continue to Phase 3

Show the exact change before writing:

```
I'll update .codecannon.yaml with:

  TICKET_LABELS: "bug,enhancement,..."

Proceed? (yes/no)
```

Wait for confirmation. Write only on yes.

---

### Phase 3 — Optional config walkthrough (profile-aware)

First, infer the current profile using the same rules as Phase 1.

The walkthrough adapts based on profile. Walk through each applicable unset optional config value in the order shown below. Skip any value that is already set. For each unset value, explain what it does in one sentence, show an example, and ask if they want to set it. If the user says "skip" or provides nothing useful, move on immediately without modifying the file. Do not ask again.

**Which values to walk through per profile:**

- **Lightweight:** `PLATFORM_COMPLIANCE_NOTES` → `CONVENTIONS_NOTES` only. Skip DEFAULT_MILESTONE, DEFAULT_REVIEWERS, TICKET_LABEL_CREATION_ALLOWED, and QA labels — the Lightweight profile intentionally leaves these unset.
- **Standard:** `DEFAULT_REVIEWERS` → `TICKET_LABEL_CREATION_ALLOWED` → `PLATFORM_COMPLIANCE_NOTES` → `CONVENTIONS_NOTES`. Skip DEFAULT_MILESTONE and QA labels unless the user asks about them.
- **Governed:** All values: `DEFAULT_MILESTONE` → `DEFAULT_REVIEWERS` → `TICKET_LABEL_CREATION_ALLOWED` → `PLATFORM_COMPLIANCE_NOTES` → `CONVENTIONS_NOTES`.
- **Custom:** Same as Governed (walk through everything).

---

### Greenfield GitHub baseline guidance (for PM/BA setup)

Before the value walkthrough, provide this mini guide when either condition is true:
- `TICKET_LABELS` is unset, or
- fewer than 5 labels exist in the repository.

Keep it short and practical:

1. Explain that `/start` works best with a clear issue-label pool (`TICKET_LABELS`) and `/qa` needs explicit QA lifecycle labels.
2. Recommend this baseline label set for new projects:
   - Work intake: `bug`, `enhancement`, `chore`, `documentation`
   - QA lifecycle: `ready-for-qa`, `qa-passed`, `qa-failed`
   - Optional planning: one lightweight priority scheme (for example `priority:high`, `priority:medium`, `priority:low`)
3. Explain milestone guidance:
   - If the team runs planned iterations, set `DEFAULT_MILESTONE` (example: `Sprint 12` or `Release 2026.04`).
   - If not, leave it unset so `/start` auto-detects open milestones and prompts only when needed.
4. End with: "Want me to help apply this baseline now during setup? (yes/no)"

If user says no, continue immediately with the normal walkthrough.

---

**DEFAULT_MILESTONE** (Governed and Custom only)

"Sets the default milestone applied to every issue `/start` creates — skip if you're not using milestones or prefer auto-detect."

Example: `DEFAULT_MILESTONE: "Sprint 4"`

Ask: "Which milestone should new issues go under, if any? (name, number, or 'skip')"

**DEFAULT_REVIEWERS** (Standard, Governed, and Custom)

"Comma-separated GitHub handles or team slugs that `/submit-for-review` adds as PR reviewers — leave unset to rely on CODEOWNERS or manual assignment."

Example: `DEFAULT_REVIEWERS: "@alice,@bob"`

Ask: "Who should be auto-assigned as PR reviewers? (handles, team slugs, or 'skip')"

**TICKET_LABEL_CREATION_ALLOWED** (Standard, Governed, and Custom)

"Controls whether `/start` can create new GitHub labels on the fly when none in the pool fit the task. Defaults to false."

Example: `TICKET_LABEL_CREATION_ALLOWED: "true"`

Ask: "Allow `/start` to create new labels when none fit? (true / false / skip)"

**PLATFORM_COMPLIANCE_NOTES** (all profiles)

"Platform-specific rules injected into the review agent — this is how the review agent catches issues specific to your infrastructure. Skip if you're not sure yet."

Ask: "What backend or infrastructure does this project use? (e.g. Postgres, Redis, Next.js, a specific ORM or framework — or 'skip')"

Wait for response. If skip → move on.

Based on their answer, draft 2–4 compliance rules that are commonly violated for those technologies and checkable by a review agent. Show the draft:

```
Here's a draft for PLATFORM_COMPLIANCE_NOTES:

  PLATFORM_COMPLIANCE_NOTES: |
    - <rule 1>
    - <rule 2>
    - <rule 3>

Does this look right? Edit, add more, or say 'looks good'.
```

Iterate until the user approves or says skip. On approval, show the exact yaml change and ask "Write this to `.codecannon.yaml`? (yes/no)". Write only on yes. Confirm with one line after writing.

**CONVENTIONS_NOTES** (all profiles)

"Non-obvious team conventions injected into the review agent — rules that differ from common defaults and that you'd want a reviewer to flag. Skip if you're not sure yet."

Ask: "What are the most commonly violated or non-obvious code conventions on this project that you'd want a reviewer to catch? (or 'skip')"

Wait for response. If skip → move on.

Shape their answer into concise, checkable rules. Show the draft:

```
Here's a draft for CONVENTIONS_NOTES:

  CONVENTIONS_NOTES: |
    - <rule 1>
    - <rule 2>

Does this look right? Edit, add more, or say 'looks good'.
```

Iterate until the user approves or says skip. On approval, show the exact yaml change and ask "Write this to `.codecannon.yaml`? (yes/no)". Write only on yes. Confirm with one line after writing.

---

### Phase 4 — Team sharing

After completing or skipping the config walkthrough, say:

"To share this setup with your team, commit these files. Anyone who clones the project and runs `git submodule update --init` will have all skills ready — no further setup needed."

Show the exact command:

```bash
git add .codecannon.yaml .claude/ CodeCannon AGENTS.md
```

Add a note: `/start` can be used to create well-formed GitHub issues without writing any code — useful for non-developers tracking work. `/status` generates standup summaries from open issues and PRs — both are valuable outside of a development workflow.

---

## Hard rules

- Only modify `.codecannon.yaml`. Do not touch any other file (except running `CodeCannon/sync.sh`, which modifies `.claude/commands/` — permitted only with explicit user approval).
- Do not run `sync.sh` without explicit user permission.
- Do not create `.codecannon.yaml` without explicit user permission.
- Do not report a configuration problem unless confident the condition is genuinely broken. Prefer false negatives over false positives on all diagnostic checks.
- Never fetch more than 100 labels in a single command. `gh label list --limit 100` is the ceiling.
- Do not skip any human gate in Phase 2 or Phase 3 — each write requires confirmation.
- If the user skips a config value, do not ask again. Move on.
<!-- generated by CodeCannon/sync.sh | skill: setup | adapter: claude | hash: e2f06373 | DO NOT EDIT — run CodeCannon/sync.sh to regenerate -->
