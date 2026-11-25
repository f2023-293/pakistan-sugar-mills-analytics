# How to put this project on GitHub and run it in Colab

## Step 1: Create the repository
1. Sign in at https://github.com with your **personal** account.
2. Click **+** (top right) → **New repository**.
3. Repository name: `pakistan-sugar-mills-analytics` (use exactly this name, the notebook expects it).
4. Choose **Public** (Colab can only clone public repos without a token).
5. Do **not** tick "Add a README" (the project already has one). Click **Create repository**.

## Step 2: Upload the files (choose ONE option)

### Option A: Upload in the browser (easiest, no Git needed)
1. Unzip `pakistan-sugar-mills-analytics.zip` on your computer.
2. On the new empty repository page click **uploading an existing file**.
3. Open the unzipped `pakistan-sugar-mills-analytics` folder, select **everything inside it**
   (`data`, `docs`, `notebooks`, `outputs`, `src`, `README.md`, `requirements.txt`, `.gitignore`, this guide)
   and drag it onto the GitHub page. Folders keep their structure in Chrome and Edge.
4. Wait until every file is listed (about 45 files, ~45 MB in total; the largest file is under 5 MB, well within GitHub's 25 MB browser limit).
   Do NOT include the .zip file itself in the upload: at ~45 MB it is over the limit and the commit will fail.
5. Commit message: `Initial commit: Pakistan sugar mills big data project` → **Commit changes**.

> `.gitignore` starts with a dot, so it may be hidden on your computer. If it does not upload, it is not critical.

### Option B: Git command line
Install Git (https://git-scm.com), then in a terminal opened inside the unzipped project folder:
```bash
git init
git add .
git commit -m "Initial commit: Pakistan sugar mills big data project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/pakistan-sugar-mills-analytics.git
git push -u origin main
```
When asked for a password, use a **Personal Access Token** (GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate, tick `repo`).

### Option C: GitHub Desktop
File → Add local repository → choose the unzipped folder → "create a repository" → Commit → **Publish repository** (untick "Keep this code private").

## Step 3: Put your username in two places
Edit these on GitHub (click the file → pencil icon) or before uploading:
1. `README.md`: replace `GITHUB_USERNAME` in the "Open in Colab" badge link.
2. `notebooks/Pakistan_Sugar_Mills_Analytics.ipynb`: in the first code cell set
   `GITHUB_USERNAME = "your-actual-username"`.
   (Easiest: open it in Colab first, change the line, then File → Save a copy in GitHub.)

## Step 4: Run in Google Colab
1. Go to https://colab.research.google.com → **File → Open notebook → GitHub** tab.
2. Paste `https://github.com/YOUR-USERNAME/pakistan-sugar-mills-analytics` and open `notebooks/Pakistan_Sugar_Mills_Analytics.ipynb`.
3. Check `GITHUB_USERNAME` in the first code cell, then **Runtime → Run all**.
4. The first cell installs PySpark and clones your repo with the data. The full run takes roughly 10 to 20 minutes on the free Colab tier
   (most of it is model training).

If cloning fails (for example the repo is private), the notebook regenerates the dataset itself only if `src/generate_data.py` is present,
so for Colab keep the repository **public**, or upload the project zip to Colab and unzip it to `/content/pakistan-sugar-mills-analytics`.
