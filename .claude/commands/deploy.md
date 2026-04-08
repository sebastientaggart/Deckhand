Code Cannon: Bump the project version, create a GitHub Release, and promote to production — handles both versioning and releasing in one step

---

## What `/deploy` does

`/deploy` is the final step in the workflow. It combines version bumping and release creation into a single command: check state, optionally bump the version, then create a GitHub Release (and in multi-branch mode, promote to production).

---

## Step 1 — Verify branch

Run:
```bash
git branch --show-current
```

Required branch: `main` (trunk mode).

If not on the required branch, abort and say: "Switch to `<required-branch>` before running `/deploy`."

Pull the latest changes before proceeding:
```bash
git pull
```

---

## Step 2 — Check current state

### Find the latest version tag

```bash
git describe --tags --abbrev=0 2>/dev/null
```

If no tag exists, note this is the first release.

### Read current version

```bash
make version
```

### Show commits since last tag

If a previous tag exists, show what's on the branch since that tag:

```bash
git log <latest-tag>..HEAD --merges --pretty=format:"%s"
```

Parse PR numbers from merge commit subjects (format: `Merge pull request #N from branch/name`).

For each PR number found, retrieve the PR body:
```bash
gh pr view <N> --json number,title,body
```

Extract `Closes #N` references from PR bodies. Compile:
- List of PRs included (number + title)
- List of issues linked to those PRs

### Check for open unmerged PRs

```bash
gh pr list --state open --json number,title,headRefName --jq '.[] | "#\(.number) \(.title) (\(.headRefName))"'
```

### Present the summary

Tell the user:

```
Current version: X.Y.Z
Latest tag: vX.Y.Z

Commits/PRs since last tag:
  #17 — Add /docs directory
  #18 — Fix checkout runtime error

Open PRs not yet merged:
  #19 — Add dark mode (feature/dark-mode)

Would you like to bump the version before deploying?
  - **patch** → X.Y.C
  - **minor** → X.B.0
  - **major** → A.0.0
  - **specific** → enter a version number
  - **skip** → proceed to release with the latest existing tag
```

Wait for their response.

---

## Step 3 — Version bump (if requested)

If the user chose to skip, find the latest version tag in the branch history:
```bash
git describe --tags --abbrev=0 2>/dev/null
```

If no tag is found at all (first release), warn: "No version tag found. You must bump the version before deploying." Return to the version bump prompt. Otherwise, use the tag found as the release version.

If the user chose a bump level, map their response to a command:

| User says | Run |
|---|---|
| "patch" / anything mentioning patch | `make bump-patch` |
| "minor" | `make bump-minor` |
| "major" | `make bump-major` |
| A specific version e.g. "2.4.5" | `make set-version V= 2.4.5` |

These commands update the version manifest, create a git commit, and create a git tag. Do not create commits or tags manually.

Push the version bump:
```bash
git push
git push --tags
```

Both the version bump commit and the tag must be pushed.

---

## Step 4 — Compute release contents

Determine the version tag (either from the bump just performed, or from the existing HEAD tag if the user skipped bumping).

Find the previous tag to determine the range:
```bash
git describe --abbrev=0 <version-tag>^ 2>/dev/null
```

Find all merge commits since the previous tag:
```bash
git log <prev-tag>..HEAD --merges --pretty=format:"%s"
```

Parse PR numbers from merge commit subjects (format: `Merge pull request #N from branch/name`).

For each PR number found, retrieve the PR body:
```bash
gh pr view <N> --json number,title,body
```

Extract `Closes #N` references from PR bodies (trunk PRs use `Closes #N`). Compile:
- List of PRs included (number + title)
- List of issues linked via `Closes #N`

---

## Step 5 — HUMAN GATE

Show the user the release summary. Example format:

```
Ready to release vX.Y.Z to production.

PRs included:
  #17 — Add /docs directory
  #18 — Fix checkout runtime error

Issues that will be referenced:
  #14 — Add /docs directory
  #15 — Fix checkout runtime error

Have you confirmed everything above is ready for production? Type 'release' to confirm.
```

Wait for the user to type "release" or an explicit confirmation. Any other response → stop and ask what they'd like to change.

---

## Step 6 — Create GitHub Release

The version tag and PR/issue list are already known. If no previous tag exists, omit the "Full changelog" line.

```bash
gh release create <version-tag> \
  --title "<version-tag>" \
  --notes "$(cat <<'EOF'
## Changes

- #<issue> — <PR title> (PR #<pr-number>)
[... one line per PR included in this release ...]

**Full changelog:** https://github.com/<owner>/<repo>/compare/<previous-tag>...<version-tag>
EOF
)"
```

Format each PR line as `- #<linked-issue> — <PR title> (PR #<N>)`. If a PR had no linked issue, use just the PR title.

After the command runs, note the release URL from the output.

---

## Step 7 — Report

Tell the user:

> "Released vX.Y.Z. Issues closed on merge. GitHub Release vX.Y.Z created at `<url>`. Run `make deploy-prod` to ship to production."
<!-- generated by CodeCannon/sync.sh | skill: deploy | adapter: claude | hash: 9ef10de9 | DO NOT EDIT — run CodeCannon/sync.sh to regenerate -->
