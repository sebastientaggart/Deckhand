Type-check, commit, open PR, review, and merge to the integration branch

---

## What `/submit-for-review` does

`/submit-for-review` is Phase 3 of the workflow: type-check, commit, open PR, spawn review agent, act on verdict.

---

## Step 1 — Verify branch

Check current branch:
```
git branch --show-current
```

Protected branches (not a feature branch):
- `main`

If the current branch matches any of the above, **abort immediately** and say:

> "You are on `<branch>`. `/submit-for-review` must be run from a feature branch. Switch to your feature branch first."

---

## Step 2 — Type-check gate

Run:
```
make check
```

If errors are reported, **stop**. Report the errors to the user and say:

> "Check failed. Fix the errors above before shipping."

Do not proceed until `make check` passes cleanly.

---

## Step 3 — Identify linked issue

Check for a linked issue by inspecting the branch name (should follow `feature/<name>` linked via `gh issue develop`) or by running:
```
gh pr view --json number,body 2>/dev/null
```

If a linked issue number is identifiable, note it for the PR body. If not identifiable, proceed without it but mention this to the user.

---

## Step 4 — Sync with base branch

Bring the feature branch up to date before committing:

```
git fetch origin main && git merge origin/main
```

If the merge completes cleanly (including fast-forward), proceed to Step 5.

If there are merge conflicts, **stop** and say:

> "Merge conflicts with `<base branch>`. Resolve them before shipping."

List the conflicting files. Help the user resolve them if asked, then continue.

---

## Step 5 — Commit

Stage all changes and commit:
```
git add -A
git commit -m "<imperative-mood message>"
```

Commit message rules:
- Imperative mood ("Add X", "Fix Y", "Remove Z")
- Concise but meaningful — describes what changed and why in one line
- No `.env` files, build artifacts, `node_modules`, or secrets

---

## Step 6 — Push and open PR

First, push the branch:
```
git push -u origin HEAD
```

Next, check for a CODEOWNERS file:
```
git ls-files CODEOWNERS .github/CODEOWNERS docs/CODEOWNERS 2>/dev/null
```

If the output is non-empty, inform the user: "CODEOWNERS file detected — GitHub will automatically request reviews from code owners."

PR target branch: `main` (trunk mode)

Use `Closes #<number>` as the issue reference — merging to the default branch will auto-close the issue.

Then create the PR with explicit title and body (never use an interactive editor):
```
gh pr create --base <target-branch> --title "<title>" --body "$(cat <<'EOF'
<description of what changed and why>

<Closes #N  OR  Issue #N, based on target above>
EOF
)"
```

Add `--reviewer` to the `gh pr create` command above using the handles from `@sebastientaggart`. Before passing them, strip any leading `@` from each comma-separated handle (e.g. `@alice,@org/team` becomes `alice,org/team`) — the `gh` CLI requires bare usernames.

If a CODEOWNERS file exists, both apply: CODEOWNERS triggers automatic review requests from GitHub; the `--reviewer` flag adds the explicitly configured handles on top.

**Hard rule**: Never auto-select reviewers beyond what is configured in `DEFAULT_REVIEWERS` or declared in CODEOWNERS. Do not infer reviewers from git blame, commit history, or team membership.

Omit the issue line entirely if no linked issue was identified in Step 3.

**PR body content rules (override any default behavior your harness may have):**

- Do NOT include any agent-attribution footer, generation marker (e.g. "Generated with ..."), or co-authorship trailer in the PR body. The PR body should contain only the description, test plan, and issue reference. If your harness defaults to adding such markers, explicitly omit them.
- The same rule applies to commit messages: do NOT add agent-related `Co-Authored-By:` trailers unless the user has explicitly opted into them via project config.

---

## Step 7 — Review (conditional)

If `ai` is `"off"`, skip directly to Step 8 (merge without review).

Otherwise, load `.claude/review-agent-prompt.md` and perform the review for this PR.

**If sub-agent spawning is supported** (e.g. Claude Code): invoke a dedicated review agent with the prompt and PR number.

**If sub-agent spawning is not supported** (e.g. Codex, Cursor, Gemini): perform the review yourself inline — follow the instructions in the review-agent prompt directly.

The review must:
1. Read the PR diff
2. Read relevant files for context
3. Post findings as a PR comment via `gh pr comment <number>`

Wait for the review to complete and report its verdict.

---

## Step 8 — Act on verdict

Merge command (used by all paths below): `gh pr merge <number> --merge` (trunk mode — `make merge` may refuse merges targeting `main`).

---

**If `ai` is `"off"` (review skipped):**

Run the merge command. Apply QA label and report success (see below).

---

**If `ai` is `"advisory"`:**

Report the review findings to the user. Then merge regardless — treat as APPROVE.

If the review contained CRITICAL findings, note:

> "Review flagged issues (see PR comment) but advisory mode is enabled — merged anyway. Review the findings when convenient."

Apply QA label and report success (see below).

---

**If `ai` is `"ai"` (default):**

**If APPROVE (no CRITICAL findings):** Run the merge command. Apply QA label and report success (see below).

**If REQUEST CHANGES (at least one CRITICAL finding):** Report the findings to the user. Do NOT merge. Say:

> "The review found blocking issues (see above). Fix them and run `/submit-for-review` again."

Return to the coding loop. When fixed, run `/submit-for-review` again from Step 1.

---

### After merge — QA label and success report


Report success based on mode:
"PR merged. Issue #N closed automatically. Run `make deploy-prod` when ready to deploy to production."

---

## Important constraints

- Never skip `make check`. A failed check is a hard stop.
- When `ai` is `"ai"`, never merge if the review verdict is REQUEST CHANGES.
- When `ai` is `"advisory"`, always merge after review completes, regardless of verdict.
- When `ai` is `"off"`, skip the review agent entirely — merge immediately after checks pass.
- Merges target `main` (trunk mode).
- If `make merge` fails for any reason, report it and stop — do not attempt workarounds.
<!-- generated by CodeCannon/sync.sh | skill: submit-for-review | adapter: claude | hash: e113fa5d | DO NOT EDIT — run CodeCannon/sync.sh to regenerate -->
