Code Cannon: Start a new feature or bugfix

---

## CRITICAL: Order of operations

**You must complete Steps 1–4 before writing any code.**
Do not open any source file with intent to edit until `git branch --show-current` shows a `feature/*` branch.

---

## Determine case

If `$ARGUMENTS` is a number (digits only) → go to **Case B: Resume existing issue**.
Otherwise → go to **Case A: New work**.

---

## Parsing $ARGUMENTS (Case A only)

> Skip this entirely if `$ARGUMENTS` triggered Case B.

The argument string may contain optional inline flags after the description. Parse as follows:

1. **Identify flags** — scan for the first token that starts with `--label`, `-l`, `--milestone`, or `-m`. Everything before it is the **description**. Everything from the first flag onward is **flags**.
2. **`--label <value>` / `-l <value>`** — comma-separated label string (e.g. `bug` or `enhancement,ux`). If provided, it **bypasses label auto-selection entirely** for this invocation — use the value verbatim. Labels containing spaces must be quoted (e.g. `--label "good first issue"`).
3. **`--milestone <value>` / `-m <value>`** — milestone name or number (e.g. `Sprint 4` or `12`). Pass the value as-is; GitHub accepts both names and numbers.
4. **Flags may appear in any order** after the description.

**Label resolution (three-tier, Case A only):**

After parsing flags, determine the active labels in this order:

1. **Per-invocation flag** — if `--label <value>` was in `$ARGUMENTS`, use that value verbatim. Skip all remaining steps.
2. **Pool-based selection** — the allowed label pool is: `bug,documentation,duplicate,enhancement,good first issue,help wanted,invalid,question,wontfix,security` (comma-separated). Select 1–3 labels from this pool that genuinely fit the task description and implementation approach. Do not apply labels mechanically — pick only what fits. If no pool label fits the task, fall through to step 3.
   - If any selected label name contains a space (e.g. `good first issue`), quote the entire `--label` value.
3. **No label / creation** — if the pool is empty or no pool label fits:
   - If label creation is allowed (`false` = `true`, case-insensitive): the agent **may** create a new label before applying it:
     ```bash
     gh label create "<name>" --color "<hex>" --description "<short description>"
     ```
     Use judgment — only create a label with clear reuse value. Do not create near-duplicates of existing pool labels.
   - Otherwise (`false` = `false` or unset): omit `--label` entirely. Proceed silently; do not inform the user.

**Milestone resolution (three-tier, Case A only):**

After parsing flags, determine the active milestone in this order:

1. **Per-invocation flag** — if `--milestone <value>` was in `$ARGUMENTS`, use that value. Stop.
3. **Auto-detect** — if no milestone is resolved yet, query open milestones:
   ```bash
   gh api repos/{owner}/{repo}/milestones --jq '[.[] | select(.state=="open")] | {count: length, milestones: [.[] | {number: .number, title: .title}]}'
   ```
   Use `gh repo view --json owner,name` first if the owner/repo are not already known.
   - **0 results** → no milestone; proceed without `--milestone`.
   - **1 result** → use its title silently. Inform the user inline: `(milestone: <title>)`.
   - **2+ results** → show the numbered list, ask once: **"Multiple open milestones — which should this issue go under? (enter a number or title, or 'none')"**. Accept milestone number, title, or "none"/"skip". Wait for response before continuing.

**Examples:**

| `$ARGUMENTS` | Description | Labels | Milestone |
|---|---|---|---|
| `Add dark mode toggle to settings page` | `Add dark mode toggle to settings page` | auto-selected from pool | auto-detected |
| `Add dark mode --label enhancement` | `Add dark mode` | `enhancement` (verbatim) | auto-detected |
| `Add dark mode --label enhancement,ux --milestone "Sprint 4"` | `Add dark mode` | `enhancement,ux` (verbatim) | `Sprint 4` |

> Replace vs append: flags **replace** auto-selection entirely, they do not append. This avoids silent label duplication and milestone conflicts.

---

## Case A: New work (text description)

### Step 1 — Investigate

Read the relevant code. Propose a concrete implementation approach. Be specific about which files change and how.

### Step 2 — HUMAN GATE

Say exactly: **"Does this approach sound right? I'll create a GitHub issue and branch before writing any code."**

Stop. Wait for the user to confirm.

The friendly text question is required regardless of harness mode. If your harness is currently in a preview / plan / dry-run mode where you cannot passively stop and wait (and must instead invoke the harness's own approval mechanism), still include the text question in your response. The harness's approval UI mediates the wait, but it is not a substitute for the question itself. Users expect to see the consistent text language across all modes; do not silently swap it for the harness's UI.

- User says yes → continue to Step 3.
- User redirects → revise approach, ask again.
- User abandons → stop. Nothing to clean up.

### Step 3 — Create GitHub Issue

Run `gh issue create` with explicit flags (do NOT open an interactive editor):

```bash
gh issue create \
  --title "<standalone full sentence — must make sense with no context>" \
  --body "<human-readable explanation: what the problem is, why it matters, general approach — written for a non-developer, no code or file paths>" \
  --assignee @me \
  [--label "<resolved labels>"] \
  [--milestone "<resolved milestone>"]
```

Resolve labels and milestone using the resolution steps in the Parsing section above:
- **Labels**: use the value from three-tier label resolution. If non-empty, add `--label "<value>"` to the command. If empty (no flag, empty pool, creation not allowed), omit `--label` entirely.
- **Milestone**: use the value from three-tier milestone resolution. If non-empty, add `--milestone "<value>"` to the command. If empty (no flag, no config default, no open milestones), omit `--milestone` entirely.

**Title rules:**
- ✅ `Fix 'Contact Us' footer link pointing to 404 instead of /contact-us`
- ❌ `Fix broken link`

After the command runs, note the issue number from the output URL (e.g. `https://github.com/.../issues/42` → issue `42`).

Show the user: `Created issue #<number>: <title>`

Then immediately post agent implementation notes as a comment:

```bash
gh issue comment <number> --body "## Agent Implementation Notes

<full technical plan: exact files to change, approach, key decisions, edge cases>"
```

### Step 4 — Create feature branch

Ensure the base branch is up-to-date before branching:

```bash
git checkout main && git pull origin main
```

Now create the feature branch:

```bash
gh issue develop <number> --name feature/<short-descriptive-name> --checkout
```


Verify the branch was created:

```bash
git branch --show-current
```

Show the user: `On branch feature/<name>`

**Do not proceed to Step 5 until this shows a `feature/*` branch.**

### Step 5 — Write the code

Now write the code. Do NOT commit anything.

When done, say: **"The code is ready for review. Please run `make dev` and test locally. Let me know if it looks good, needs changes, or should be scrapped. When you're happy, run `/submit-for-review` to commit, push, and open a PR."**

- User says looks good → run `/submit-for-review`
- User requests changes → iterate, repeat this message
- User says scrap it → run `make abandon`

---

## Case B: Resume existing issue (numeric argument)

### Step 1 — Load context

```bash
gh issue view <number> --comments
```

Read the full body and all comments. Note: what was done, what remains, branch status.

### Step 2 — Summarize and gate

Tell the user:
- What the issue is about
- What was previously done (from agent notes if present)
- What appears to remain

Ask: **"Does this match your understanding? Continue this ticket, or open a fresh one?"**

- Continue → Step 3.
- New ticket → restart as Case A with a new description.

### Step 3 — Check out branch

Ensure the base branch is up-to-date before branching:

```bash
git checkout main && git pull origin main
```

Find and check out the existing branch, or create a new one linked to the issue:

```bash
gh issue develop <number> --name feature/<short-name> --checkout
```


Verify:

```bash
git branch --show-current
```

Post a resumption comment:

```bash
gh issue comment <number> --body "Resuming work. <brief note on what's being continued.>"
```

### Step 4 — Write the code

Continue from where work left off. Do NOT commit.

When done, say: **"The code is ready for review. Please run `make dev` and test locally. When you're happy, run `/submit-for-review` to commit, push, and open a PR."**

---

## Hard rules

- Do not write or edit any source file before `git branch --show-current` shows `feature/*`.
- Do not use `make branch` — always use `gh issue develop` so the branch is linked to the issue in GitHub.
- Do not commit during `/start` — commits happen in `/submit-for-review`.
- If already on a feature branch when `/start` is invoked, warn the user before creating another branch.
- `gh issue create` must use `--title` and `--body` flags. Never open an interactive editor.
- The issue is assigned to `@me` at creation. If you are creating a ticket on someone else's behalf, remove the assignee after creation with `gh issue edit <number> --remove-assignee @me`.
- Apply resolved labels and milestone to every new issue. Label resolution order: per-invocation flag → pool selection from `bug,documentation,duplicate,enhancement,good first issue,help wanted,invalid,question,wontfix,security` → omit (or, when `false` = `true`, create). Never apply a label outside `bug,documentation,duplicate,enhancement,good first issue,help wanted,invalid,question,wontfix,security` unless `false` = `true`.
- Milestone resolution order: per-invocation flag → auto-detected from GitHub open milestones. Never prompt for a milestone more than once per invocation.
<!-- generated by CodeCannon/sync.sh | skill: start | adapter: claude | hash: 156ca39e | DO NOT EDIT — run CodeCannon/sync.sh to regenerate -->
