# GitHub Beginner Guide

Use these steps to download this project, make a change, and send it to GitHub.

## Before you start

Install [Git](https://git-scm.com/downloads) and create a GitHub account. Open Terminal (macOS/Linux) or Git Bash (Windows).

## 1. Clone the project

Copy and run these commands:

```bash
git clone https://github.com/shouta256/LostandFound.git
cd LostandFound
```

This downloads the project to a new `LostandFound` folder and moves into it.

## 2. Create a branch

Use a branch for your work. Replace `my-change` with a short name for your change.

```bash
git switch -c my-change
```

## 3. Write code

Open the folder in your code editor, make your changes, and save the files.

Check what changed:

```bash
git status
```

## 4. Save your change in Git

Add the files you want to save, then create a commit.

```bash
git add .
git commit -m "Describe your change"
```

Use a short message that explains what you changed.

## 5. Push to GitHub

```bash
git push -u origin my-change
```

Replace `my-change` with the branch name from step 2. If GitHub asks you to sign in, complete the sign-in in your browser or use a personal access token when requested.

## 6. Create a pull request

Open the repository page on GitHub. GitHub will usually show a **Compare & pull request** button for your new branch. Select it, write a short description, and create the pull request.

## Later updates

For more changes on the same branch, repeat these commands:

```bash
git add .
git commit -m "Describe your next change"
git push
```

## Helpful commands

```bash
git status       # Show changed files
git branch       # Show your current branch
git pull origin main  # Download the latest main branch changes
```
