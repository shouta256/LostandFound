GitHub Beginner Guide

Use these steps to download this project, make changes, and send them to GitHub.

GitHub Workflow

Follow these rules when working on this project:

Never push directly to the main branch.

Create a separate branch for each change or task.

Open a pull request to merge changes into main.

Shota is the primary code reviewer and normally approves pull requests.

If Shota creates the pull request, another team member must review and approve it.

A pull request needs at least 1 approval before it can be merged into main.

After a pull request is merged, start new work from the latest main branch.

Before you start

Install Git and create a GitHub account.

Open:

Terminal on macOS/Linux

Git Bash on Windows

1. Clone the project

Run:

git clone https://github.com/shouta256/LostandFound.git
cd LostandFound

This downloads the project into a new LostandFound folder and moves into it.

You only need to clone the repository once.

2. Update main

Before starting new work, make sure your local main branch is up to date.

git switch main
git pull origin main

Always update main before creating a new branch.

3. Create a branch

Create a new branch for your work.

git switch -c my-change

Replace my-change with a short name describing your task.

Examples:

git switch -c login-page
git switch -c lost-item-form
git switch -c database-setup
git switch -c fix-navbar

You can check which branch you are currently using with:

git branch

The branch with * is your current branch.

Example:

  main
* lost-item-form

Do not make project changes directly on main.

4. Write code

Open the project folder in your code editor and make your changes.

After saving your files, check what changed:

git status

This shows modified, added, and deleted files.

5. Save your changes with a commit

Add your changes:

git add .

Then create a commit:

git commit -m "Describe your change"

Use a short message that explains what you changed.

Examples:

git commit -m "Add lost item form"
git commit -m "Fix navbar layout"
git commit -m "Add database connection"

6. Push your branch to GitHub

Push your branch:

git push -u origin my-change

Replace my-change with your actual branch name.

For example:

git push -u origin lost-item-form

The -u option is normally needed only the first time you push a new branch.

After that, you can usually use:

git push

Do not push directly to main

Do not run:

git push origin main

The main branch is protected, so direct pushes are blocked.

Changes must go through a pull request.

7. Create a pull request

After pushing your branch, open the repository on GitHub:

https://github.com/shouta256/LostandFound

GitHub will usually show a Compare & pull request button.

Then:

Click Compare & pull request

Make sure the base branch is main

Make sure the compare branch is your branch

Add a short title

Write a short description of what you changed

Create the pull request

For example:

base: main ← compare: lost-item-form

8. Code review and approval

Shota is the primary code reviewer for this project.

For most pull requests:

Create the pull request

Ask Shota to review it

Shota reviews the code

Fix anything requested during the review

Shota approves the pull request

Merge the pull request into main

A pull request requires at least 1 approval before it can be merged.

If Shota creates the pull request

Shota cannot provide the required approval for his own pull request.

In this case:

Shota creates the pull request

Another team member reviews it

That team member approves it

The pull request can then be merged

9. Fix problems found during code review

If your pull request has not been merged yet and Shota requests changes, stay on the same branch.

Make the requested changes, then run:

git add .
git commit -m "Fix review comments"
git push

You do not need to create another pull request.

The existing pull request updates automatically when you push new commits to the same branch.

10. After the pull request is merged

Once your pull request has been merged, do not keep using that branch for unrelated work.

Return to main:

git switch main

Download the newest version:

git pull origin main

Then create a new branch for your next task:

git switch -c another-change

For example:

git switch main
git pull origin main
git switch -c search-page

The normal workflow is:

main
 ↓
create new branch
 ↓
write code
 ↓
commit
 ↓
push branch
 ↓
pull request
 ↓
code review
 ↓
approval
 ↓
merge into main
 ↓
update local main
 ↓
create another branch

Updating an existing pull request

If your pull request is still open and you want to add more changes, stay on the same branch.

Run:

git add .
git commit -m "Describe your next change"
git push

The pull request will automatically include the new commit.

You do not need to create a second pull request.

If main changed while you were working

Sometimes another pull request may be merged into main while you are still working on your branch.

GitHub may show an Update branch option on your pull request.

You can use it to update your branch with the newest changes from main.

If there is a merge conflict, do not randomly delete conflicting code. Ask Shota if you are unsure how to resolve it.

Helpful commands

Check your current branch

git branch

Check changed files

git status

Switch to main

git switch main

Update your local main

First switch to main:

git switch main
git pull origin main

Create a new branch

git switch -c branch-name

Add changed files

git add .

Create a commit

git commit -m "Describe your change"

Push a new branch for the first time

git push -u origin branch-name

Push later commits on the same branch

git push

See recent commits

git log --oneline

Important

Do not use these commands unless you know exactly what they do:

git push --force
git reset --hard

If you encounter an error, merge conflict, or Git problem that you do not understand, ask Shota before trying to fix it with destructive Git commands.
