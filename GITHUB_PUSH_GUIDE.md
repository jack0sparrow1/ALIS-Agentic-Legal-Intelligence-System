# How to Push ALIS to GitHub

## Step-by-Step Guide

### 1️⃣ Create GitHub Repository

1. Go to https://github.com/new
2. **Repository name**: `ALIS`
3. **Description**: `Agentic Legal Intelligence System - Legal Q&A with FAISS and LLM`
4. **Public** (recommended for portfolio)
5. **Do NOT initialize with README** (we have one)
6. Click **Create repository**

You'll see a page with commands. Copy the HTTPS URL.

---

### 2️⃣ Initialize Git Locally

Open PowerShell/Terminal in `d:/ALIS`:

```bash
cd d:/ALIS
```

Initialize git:
```bash
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

---

### 3️⃣ Add Files to Git

```bash
# Check what will be included (respecting .gitignore)
git status

# Stage all files
git add .

# Verify files being added
git status
```

**What gets included:**
✅ `app.py`, `requirements.txt`, README.md
✅ Source code in `src/`, `data_preprocessing/`
✅ Documentation in `docs/` (all .md files)
✅ `.gitignore`

**What gets EXCLUDED** (by .gitignore):
❌ `.env` (credentials safe!)
❌ `data/` (2.1 MB JSONL files)
❌ `ALIS_venv/` (virtual environment)
❌ `__pycache__/`, `.streamlit/`
❌ Model cache files

---

### 4️⃣ Create Initial Commit

```bash
git add .
git commit -m "Initial commit: ALIS legal AI system with FAISS retrieval"
```

---

### 5️⃣ Connect to GitHub

Replace `YOUR_USERNAME` with your GitHub username:

```bash
git remote add origin https://github.com/YOUR_USERNAME/ALIS.git
```

Verify:
```bash
git remote -v
```

Should show:
```
origin  https://github.com/YOUR_USERNAME/ALIS.git (fetch)
origin  https://github.com/YOUR_USERNAME/ALIS.git (push)
```

---

### 6️⃣ Push to GitHub

```bash
git branch -M main
git push -u origin main
```

If asked for credentials:
- **Username**: Your GitHub username
- **Password**: Use a Personal Access Token (not your password)

---

### 7️⃣ Generate Personal Access Token (if needed)

If push fails with authentication error:

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. **Token name**: `ALIS Push`
4. **Expiration**: 30 days
5. **Scopes**: Check `repo` (full control of private repositories)
6. Click **Generate token**
7. **Copy** the token (you won't see it again!)
8. Use as password when `git push` asks

---

## ✅ What Gets Pushed

### Code Files
```
app.py                          (Main app - 260 lines)
requirements.txt                (Dependencies)
README.md                       (Project overview)
.gitignore                      (What to exclude)

src/
├── agent-controller.py         (Agent logic)
├── graph_verification.py       (Reasoning extraction)
├── memory_integration.py       (Conversation memory)
└── search_test.py             (Search utilities)

data_preprocessing/
├── IPC_preprocessing.py        (IPC parser)
├── IT_ACT_preprocessing.py     (IT Act parser)
└── crpc_preprocessing.py       (CRPC parser)

docs/
├── FAISS_DEEP_DIVE.md          (Current system - 450 lines)
├── ELASTICSEARCH_DEEP_DIVE.md  (Historical - 500 lines)
├── ELASTICSEARCH_VISUAL.md     (Diagrams - 400 lines)
├── INTERVIEW_GUIDE.md          (Interview prep - 300 lines)
├── FAISS_MIGRATION.md          (Migration notes)
├── DOCUMENTATION_INDEX.md      (Guide to docs)
└── MEMORY.md                   (Quick reference)
```

**Total size**: ~150 KB (very small!)

### What's NOT Pushed
```
✗ .env (credentials)
✗ data/ (2.1 MB of legal docs)
✗ ALIS_venv/ (500 MB virtual env)
✗ __pycache__/ (Python cache)
✗ .streamlit/ (local config)
✗ Model downloads
```

---

## 🎯 Verification

After push, verify on GitHub:

```bash
# Check if files are there
git log --oneline
git remote -v

# See pushed files
Enter your GitHub repo URL
```

Should show all files **except** .env and data/

---

## 📝 What to Show in Your Portfolio

### README has:
✅ Project overview
✅ Quick start guide
✅ Architecture diagram
✅ Tech stack
✅ How to run locally
✅ Performance metrics
✅ Contributing guidelines

### You wrote comprehensive docs:
✅ FAISS_DEEP_DIVE.md - Technical depth
✅ INTERVIEW_GUIDE.md - Communication skills
✅ Multiple documentation files - Attention to detail

---

## 💡 Tips

**Make repo stand out:**
1. ✅ Good README (you have it)
2. ✅ Clear code structure
3. ✅ Well-documented (.md files)
4. ✅ Open source license (included)
5. ✅ Quick start guide (in README)

**For interviews:**
- This shows: "I think about deployment, documentation, security"
- Credentials in .env: "I know security best practices"
- FAISS over ES: "I can make pragmatic architecture decisions"
- Comprehensive docs: "I can communicate clearly"

---

## 🚀 Quick Commands Summary

```bash
cd d:/ALIS

# One-time setup
git init
git config user.name "Your Name"
git config user.email "your@email.com"

# Add files
git add .

# Commit
git commit -m "Initial commit: ALIS legal AI system with FAISS"

# Connect to GitHub
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ALIS.git

# Push
git push -u origin main
```

Done! 🎉

---

## 📋 Post-Push Checklist

- [ ] GitHub repo created
- [ ] Local git initialized
- [ ] All files committed
- [ ] Pushed to GitHub
- [ ] Verify files on GitHub website
- [ ] Share repo link with interviewers
- [ ] Add to LinkedIn/Resume

