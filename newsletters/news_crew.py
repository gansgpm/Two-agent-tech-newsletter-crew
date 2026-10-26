"""
news_crew.py
Week 4 - Day 4 | Social Eagle Gen AI Architect Program
Build a Two-Agent Crew for a Tech Newsletter

Two agents work in a line (Process.sequential):
  1. Researcher -> searches the web with SerperDevTool and finds the day's top 3 tech stories
  2. Writer     -> has NO tools; turns the Researcher's brief into a 5-line newsletter

The Researcher's output is handed to the Writer explicitly with context=[find].

Keys are read from environment variables (loaded from a local .env file):
  OPENAI_API_KEY, SERPER_API_KEY, MODEL (optional, defaults to gpt-4.1-mini)

Usage:
  python news_crew.py                      # today's news
  python news_crew.py --date yesterday     # yesterday's news
  python news_crew.py --date 2026-10-20    # news from a specific past date
"""

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Tuple

import requests
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task, TaskOutput
from crewai_tools import SerperDevTool

# ---------------------------------------------------------------------------
# 0. Setup: load keys from .env and fail early with a clear message
# ---------------------------------------------------------------------------
# Load .env from the same folder as this script; override=True makes .env win
# over any old value already set in the terminal or in Windows settings.
load_dotenv(Path(__file__).parent / ".env", override=True)

# Windows terminals sometimes choke on emoji in CrewAI's verbose logs
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

bad_keys = [
    key
    for key in ("OPENAI_API_KEY", "SERPER_API_KEY")
    if not os.getenv(key) or "your-" in os.getenv(key, "")
]
if bad_keys:
    sys.exit(
        f"Missing or placeholder key(s): {', '.join(bad_keys)}\n"
        "Open the .env file next to news_crew.py, replace the placeholder values "
        "with your real keys, and save it (as .env, not .env.txt)."
    )

os.environ.setdefault("MODEL", "gpt-4.1-mini")  # CrewAI reads the LLM name from MODEL


# ---------------------------------------------------------------------------
# 1. The search tool (only the Researcher gets it)
# ---------------------------------------------------------------------------
class DateFilteredSerperDevTool(SerperDevTool):
    """SerperDevTool plus an optional Google date filter.

    CrewAI's SerperDevTool has no setting for Google's time filter (`tbs`), so this
    subclass adds one. When `tbs` is empty it behaves exactly like SerperDevTool.
    Example: tbs="cdr:1,cd_min:10/25/2026,cd_max:10/25/2026" -> only news from 25 Oct 2026.
    """

    tbs: str = ""

    def _make_api_request(self, search_query: str, search_type: str) -> dict[str, Any]:
        if not self.tbs:
            return super()._make_api_request(search_query, search_type)
        response = requests.post(
            self._get_search_url(search_type),
            headers={
                "X-API-KEY": os.environ["SERPER_API_KEY"],
                "content-type": "application/json",
            },
            json={"q": search_query, "num": self.n_results, "tbs": self.tbs},
            timeout=15,
        )
        response.raise_for_status()
        return dict(response.json())


# search_type="news" hits Serper's Google News endpoint, so the stories are fresh
# and change from one day to the next.
search = DateFilteredSerperDevTool(search_type="news", n_results=10)

# ---------------------------------------------------------------------------
# 2. The two agents
# ---------------------------------------------------------------------------
researcher = Agent(
    role="Senior Tech News Researcher",
    goal=(
        "Find the 3 most important technology news stories published on {news_date} "
        "and report them as verified facts with their sources."
    ),
    backstory=(
        "You are a seasoned technology journalist who scans the news every morning. "
        "You separate real news (launches, funding, regulation, research, big deals) "
        "from noise (opinion pieces, listicles, discounts). You never invent a story: "
        "every fact you report comes from a search result, with its source and link."
    ),
    tools=[search],
    allow_delegation=False,
    verbose=True,
)

writer = Agent(
    role="Tech Newsletter Writer",
    goal="Turn the researcher's 3 stories into a crisp, accurate 5-line newsletter.",
    backstory=(
        "You write a daily newsletter for busy professionals who have 30 seconds to "
        "spare. You do not research: you work only from the brief handed to you, "
        "and you never add facts that are not in it. Every word must earn its place."
    ),
    tools=[],  # no tools on purpose: a Writer with search would research again
    allow_delegation=False,
    verbose=True,
)

# ---------------------------------------------------------------------------
# 3. The two tasks
# ---------------------------------------------------------------------------
find = Task(
    description=(
        "This newsletter is for {news_date}. Search the web for the top technology "
        "news of that day. Run at least two different searches (for example "
        "'technology news {news_date}' and 'AI news {news_date}') so you see a broad "
        "set of stories. From the results, pick the 3 most important and DISTINCT "
        "tech stories published on {news_date}. Skip opinion pieces, listicles, "
        "shopping deals and duplicate coverage of the same event. "
        "Use only what the search results say; do not invent details."
    ),
    expected_output=(
        "Exactly 3 stories in the format below, and nothing else:\n"
        "STORY 1\n"
        "Headline: <the headline>\n"
        "Summary: <1-2 factual sentences: what happened and who is involved>\n"
        "Source: <publication name> | <URL>\n"
        "Date: <publication date>\n"
        "\n"
        "STORY 2\n"
        "(same four fields)\n"
        "\n"
        "STORY 3\n"
        "(same four fields)"
    ),
    agent=researcher,
)


def exactly_five_lines(result: TaskOutput) -> Tuple[bool, Any]:
    """Guardrail: reject the newsletter (and make the Writer retry) unless it is 5 lines."""
    lines = [line.strip() for line in result.raw.strip().splitlines() if line.strip()]
    lines = [line for line in lines if not line.startswith("```")]  # drop code fences
    if len(lines) != 5:
        return (
            False,
            f"The newsletter must be exactly 5 lines, but you wrote {len(lines)}. "
            "Rewrite it as: 'Tech in 5 lines', three numbered story lines, "
            "and one line starting with 'Why it matters:'.",
        )
    if not lines[4].lower().startswith("why it matters"):
        return (False, "Line 5 must start with 'Why it matters:'. Rewrite the newsletter.")
    return (True, "\n".join(lines))


write = Task(
    description=(
        "Using ONLY the 3 stories in the Researcher's brief (provided to you as context), "
        "write the tech newsletter for {news_date}. "
        "Each story line is one sentence of under 30 words that names the company or "
        "subject and says what happened. The last line connects the three stories into "
        "one takeaway for a busy professional. Do not add facts that are not in the brief. "
        "No markdown, no bold, no blank lines, no text before or after the newsletter."
    ),
    expected_output=(
        "Exactly 5 lines of plain text, in this format:\n"
        "Tech in 5 lines\n"
        "1. <first story, one sentence>\n"
        "2. <second story, one sentence>\n"
        "3. <third story, one sentence>\n"
        "Why it matters: <one sentence linking the three stories>"
    ),
    agent=writer,
    context=[find],  # hand the Researcher's output to the Writer
    guardrail=exactly_five_lines,  # bonus: enforce the 5-line rule in code
    guardrail_max_retries=2,
)

# ---------------------------------------------------------------------------
# 4. The crew: two agents, two tasks, run in order
# ---------------------------------------------------------------------------
crew = Crew(
    agents=[researcher, writer],
    tasks=[find, write],
    process=Process.sequential,
    verbose=True,
)


def parse_run_date() -> date:
    """Read --date from the command line: 'today' (default), 'yesterday' or YYYY-MM-DD."""
    parser = argparse.ArgumentParser(description="Two-agent CrewAI tech newsletter")
    parser.add_argument(
        "--date",
        default="today",
        help="Newsletter date: 'today' (default), 'yesterday', or YYYY-MM-DD, e.g. 2026-10-25",
    )
    value = parser.parse_args().date.strip().lower()
    if value == "today":
        return date.today()
    if value == "yesterday":
        return date.today() - timedelta(days=1)
    try:
        run_date = date.fromisoformat(value)
    except ValueError:
        parser.error(f"'{value}' is not a valid date. Use YYYY-MM-DD, e.g. 2026-10-25.")
    if run_date > date.today():
        parser.error("The date cannot be in the future.")
    return run_date


def save_run(newsletter: str, brief: str, run_date: date) -> Path:
    """Save the newsletter and the research brief, one file per date, so runs can be compared."""
    out_dir = Path(__file__).parent / "newsletters"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"newsletter_{run_date.isoformat()}.txt"
    out_file.write_text(
        f"{newsletter}\n\n"
        f"--- Research brief (sources) ---\n{brief}\n",
        encoding="utf-8",
    )
    return out_file


if __name__ == "__main__":
    run_date = parse_run_date()
    news_date = run_date.strftime("%d %B %Y")  # e.g. 25 October 2026

    if run_date != date.today():
        # Restrict the news search to that single day (Google custom date range)
        us_date = run_date.strftime("%m/%d/%Y")
        search.tbs = f"cdr:1,cd_min:{us_date},cd_max:{us_date}"

    print(f"\nRunning the tech newsletter crew for {news_date} ...\n")
    result = crew.kickoff(inputs={"news_date": news_date})

    newsletter = result.raw.strip()
    brief = result.tasks_output[0].raw.strip()

    print("\n" + "=" * 60)
    print(newsletter)
    print("=" * 60)
    print(f"Saved to: {save_run(newsletter, brief, run_date)}")
