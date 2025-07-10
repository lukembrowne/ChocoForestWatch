---
description: "Complete git workflow: commit changes, merge dev to main, create PR, and auto-merge"
allowed-tools: ["Bash"]
---

# Ship to Main Workflow

Complete the full git workflow from dev to main branch:

1. **Commit current changes** on dev branch
2. **Create and push PR** from dev to main  
3. **Auto-merge the PR** (if checks pass)

## Usage
```
/project:ship-to-main [commit-message]
```

If no commit message provided, will use a default message. Do not attribute Claude or include a test plan.

## Workflow Steps

### 1. Commit and Push Current Changes
```bash
# Add all changed files
git add .

# Commit with provided message or default
git commit -m "$ARGUMENTS" || git commit -m "feat: Update codebase"

# Push current branch (dev)
git push origin dev
```

### 2. Create Pull Request
```bash
# Create PR using GitHub CLI
gh pr create --title "Merge dev into main" --body "$(cat <<'EOF'
## Summary
- Merge latest dev branch changes into main
- Includes all recent commits and improvements
EOF
)" --base main --head dev
```

### 3. Auto-merge PR (if checks pass)
```bash
# Enable auto-merge for the PR
gh pr merge --auto --squash
```

This command automates the complete workflow for deploying dev changes to main.