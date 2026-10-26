# Tech in 5 Lines: A Two-Agent CrewAI Newsletter

**Week 4 · Day 4 assignment, Social Eagle Gen AI Architect Program**

A [CrewAI](https://docs.crewai.com) crew where two agents work in a line:

| Agent | Tools | Job |
|---|---|---|
| **Researcher** | `SerperDevTool` (Google News search) | Finds today's top 3 tech news stories, with sources |
| **Writer** | none | Turns the Researcher's brief into a 5-line newsletter |

The tasks run with `Process.sequential`, and the Researcher's output is handed to the Writer through `context=[find]`.

```
            today's date
                 │
                 ▼
┌───────────────────────────────┐     context=[find]     ┌──────────────────────────────┐
│ Researcher  (SerperDevTool)   │ ─────────────────────▶ │ Writer  (no tools)           │
│ Task: find                    │   3 structured stories │ Task: write                  │
│ → 3 stories + sources         │                        │ → exactly 5 lines            │
└───────────────────────────────┘                        └──────────────────────────────┘
                                                                        │
                                                                        ▼
                                                    printed + saved to newsletters/
```

---

## Design decisions ("Think it through")

**1. How does the Writer get the Researcher's output?**
In a sequential crew the second task does not automatically see the first task's result. The `write` task declares `context=[find]`, so CrewAI injects the Researcher's final answer into the Writer's prompt.

**2. What does the Researcher hand over?**
The Researcher's `expected_output` asks for a fixed, labelled structure, so the Writer gets clean input instead of a wall of search results:

```
STORY 1
Headline: ...
Summary: 1-2 factual sentences
Source: publication | URL
Date: ...
(then STORY 2, STORY 3)
```

**3. What does "5 lines" mean?**
A title line, three story lines and one takeaway line, matching the sample output in the brief:

```
Tech in 5 lines
1. <first story, one line>
2. <second story, one line>
3. <third story, one line>
Why it matters: <one line>
```

This is stated in the Writer's `expected_output`. As a bonus, a small **guardrail** function (`exactly_five_lines`) checks the result in code and sends the Writer back to rewrite (up to 2 retries) if it is not exactly 5 lines.

**4. Why does only the Researcher get tools?**
A Writer with a search tool tends to go and research again instead of writing. Keeping `tools=[]` on the Writer keeps the roles separate.

**5. How do the stories stay fresh?**
`SerperDevTool(search_type="news")` queries Google News, and today's date is passed in through `crew.kickoff(inputs={"today": ...})`, so each day's run picks up that day's stories.

---

## Project structure

```
week4-day4-news-crew/
├── news_crew.py       # the whole crew (single file, as required)
├── requirements.txt   # crewai[tools], python-dotenv
├── .env.example       # template for your keys (safe to commit)
├── .env               # your real keys (NOT committed, blocked by .gitignore)
├── .gitignore
├── README.md
└── newsletters/       # created on first run: one file per day
```

---

## Setup (Windows, PowerShell)

> Requires Python 3.10 to 3.13. Check with `python --version`.

```powershell
# 1. Go to the project folder
cd C:\Users\<your-name>\week4-day4-news-crew

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
#   If PowerShell blocks the script, run this once, then activate again:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your keys
copy .env.example .env      # skip if .env already exists
notepad .env                # paste your OpenAI and Serper keys, save, close
```

<details>
<summary>macOS / Linux</summary>

```bash
cd ~/week4-day4-news-crew
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env with your keys
```
</details>

### Getting the keys

| Key | Where |
|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `SERPER_API_KEY` | https://serper.dev (sign up, free credits, copy the API key from the dashboard) |
| `MODEL` | Optional. Defaults to `gpt-4.1-mini` |

The `.env` file looks like this (no quotes, no spaces around `=`):

```
OPENAI_API_KEY=sk-...
SERPER_API_KEY=abc123...
MODEL=gpt-4.1-mini
```

`news_crew.py` loads it with `python-dotenv`, so you do not need to `export` / `$env:` the keys every time.

---

## Run

```powershell
python news_crew.py
```

With `verbose=True` you will see the Researcher calling **Search the internet with Serper**, then the Writer drafting. The run ends with:

```
============================================================
Tech in 5 lines
1. <first story, one line>
2. <second story, one line>
3. <third story, one line>
Why it matters: <one line>
============================================================
Saved to: ...\newsletters\newsletter_2026-10-26.txt
```

Each run is saved to `newsletters/newsletter_<date>.txt` together with the Researcher's brief and sources. Run it on two different days and compare the two files to confirm the stories change.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Missing environment variable(s)` | `.env` is missing or in the wrong folder. It must sit next to `news_crew.py`. |
| Notepad saved it as `.env.txt` | In File Explorer turn on *View → File name extensions* and rename it to `.env`. |
| `401` / `Incorrect API key` | The key in `.env` is wrong or still the placeholder. |
| `403` from Serper | Serper key wrong or free credits used up. |
| `ModuleNotFoundError: crewai` | The virtual environment is not active. Run `.\venv\Scripts\Activate.ps1`. |
| Install fails on Python 3.14 | CrewAI supports Python 3.10 to 3.13. Install 3.12 and recreate the venv. |

---

## Push to GitHub

1. On https://github.com click **New repository**, name it `week4-day4-news-crew`, keep it **Public**, and **do not** tick "Add a README" (this project already has one). Click **Create repository**.
2. In the project folder:

```powershell
git init
git add .
git status                 # .env must NOT appear in the list
git commit -m "Week 4 Day 4: two-agent CrewAI tech newsletter"
git branch -M main
git remote add origin https://github.com/<your-username>/week4-day4-news-crew.git
git push -u origin main
```

3. Sign in when Git Credential Manager opens a browser window (GitHub no longer accepts your account password on the command line).
4. Open the repository page and confirm `.env` is **not** there, but `.env.example` is.

To push later changes:

```powershell
git add .
git commit -m "Describe the change"
git push
```

> **If a key ever reaches GitHub:** revoke it immediately on the OpenAI / Serper dashboard and create a new one. Deleting the file afterwards is not enough, because it stays in the Git history.

---

## Submission checklist

- [ ] `news_crew.py` pushed to GitHub, link shared in WhatsApp
- [ ] Screenshot of one full run showing the Researcher searching and the 5-line newsletter
- [ ] Screen-recorded video of the crew running, posted in the community
- [ ] Ran on two different days and confirmed the stories changed

---

*Submitted by Remya, Social Eagle Gen AI Architect Program.*
