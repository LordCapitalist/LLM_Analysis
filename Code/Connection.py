"""citation_pipeline.py — Self‑contained GPT‑4 citation logger + validator
====================================================================
Workflow
--------
1. **Prompt** your Azure‑hosted GPT‑4 deployment with a claim. The assistant must reply with **exactly five** APA references.
2. **Log** the full assistant message to `Data/output.csv` (quote‑safe).
3. **Extract** every reference line (robust to quotes, bullets, Unicode dashes).
4. **Validate** each reference  
   • DOI present → CrossRef title‑prefix match (≥ 0.70)  
   • No DOI       → OpenAlex fuzzy title match (≥ 0.70)
5. **Write** `Data/validated_output.csv` with `status = valid / metadata_error / not_found`.

Run this script as many times as you like — each run appends a new row and re‑validates the entire log.

Prerequisites
-------------
```bash
pip install pandas requests rapidfuzz habanero azure-ai-projects azure-identity
```

Environment
-----------
* `az login` (or service‑principal) so **DefaultAzureCredential** works.  
* Update `ENDPOINT` and `DEPLOYMENT_NAME` for your own Azure AI project.
"""
from __future__ import annotations

# --------------------------------------------------------------------
# Imports & global config
# --------------------------------------------------------------------
import pathlib, re, csv, time, unicodedata, requests
from datetime import datetime
import pandas as pd
from rapidfuzz import fuzz
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
import ctypes

CROSSREF_TOLERANCE = 0.65  # Lowered for more tolerance
OPENALEX_TOLERANCE = 0.70
RATE_LIMIT_PER_S   = 3  # polite API throttle

BASE_DIR  = pathlib.Path(__file__).resolve().parent
DATA_DIR  = BASE_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH  = DATA_DIR / "output.csv"
OUT_PATH  = DATA_DIR / "validated_output.csv"

ENDPOINT        = "https://project-02445.services.ai.azure.com/api/projects/project-02445"
DEPLOYMENT_NAME = "gpt-4o"  # Azure deployment name

# Prevent Windows from sleeping while script runs
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

# --------------------------------------------------------------------
# Helper: detect a citation line
# --------------------------------------------------------------------

def is_citation_line(raw: str) -> bool:
    return bool(raw.strip())

# --------------------------------------------------------------------
# Step 1 – Prompt GPT‑4 and log response
# --------------------------------------------------------------------

def log_single_prompt(prompt: str, temperature: float = 0.7) -> None:
    """Send *prompt* to GPT‑4; append assistant message to output.csv."""
    client  = AIProjectClient(endpoint=ENDPOINT, credential=DefaultAzureCredential())

    agent = client.agents.create_agent(
        model=DEPLOYMENT_NAME,
        name="citation-agent",
        instructions=(
            "System: You are a bibliography assistant. "
            "Return exactly five APA formatted sources that support the user's claim. Answer in the following format:\n"
            "1. \n"
            "2. \n"
            "3. \n"
            "4. \n"
            "5. \n"
            "Return **only** the references  no commentary."
        ),
        temperature=temperature,
    )

    thread = client.agents.threads.create()
    client.agents.messages.create(thread_id=thread.id, role="user", content=prompt)

    run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    if run.status == "failed":
        raise RuntimeError(run.last_error)

    msgs = client.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)

    records = [{
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "thread_id": thread.id,
        "run_id"   : run.id,
        "role"     : m.role,
        "content"  : m.text_messages[-1].text.value,
    } for m in msgs if m.run_id == run.id and m.text_messages]

    pd.DataFrame(records).to_csv(
        CSV_PATH,
        mode="a",
        header=not CSV_PATH.exists(),
        index=False,
        quoting=csv.QUOTE_ALL,
    )
    print(f"[log] added {len(records)} assistant row → {CSV_PATH}")
    client.agents.delete_agent(agent.id)

# --------------------------------------------------------------------
# Validation helpers (CrossRef / OpenAlex)
# --------------------------------------------------------------------

doi_re   = re.compile(r"10\.\d{4,9}/[\w.\-()/]+", re.I)
title_re = re.compile(r"\(\d{4}\)\.\s*(.+?)\.", re.S)


def _clean(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt).lower()
    # Keep hyphens (important for medical titles)
    txt = re.sub(r"[^a-z0-9\- ]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _crossref_ok(doi: str, cited_title: str) -> bool:
    r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=8)
    if r.status_code == 200:
        real_title = r.json()["message"].get("title", [""])[0]
        if real_title:                                    # normal path
            score = fuzz.token_set_ratio(_clean(real_title), _clean(cited_title))/100
            return score >= 0.80
        # metadata missing → fall back to simple DOI resolve check
    # try a HEAD request to see if doi.org resolves
    return requests.head(f"https://doi.org/{doi}", allow_redirects=True, timeout=6).status_code == 200


def _openalex_ok(title: str) -> bool:
    r = requests.get("https://api.openalex.org/works", params={"search": title, "per_page": 1}, timeout=8)
    if r.status_code != 200 or r.json()["meta"].get("count", 0) == 0:
        return False
    hit_title = r.json()["results"][0]["title"]
    score = fuzz.token_set_ratio(_clean(title), _clean(hit_title))/100
    return score >= OPENALEX_TOLERANCE


def google_books_ok(title: str) -> bool:
    """Check if a book with a similar title exists in Google Books."""
    r = requests.get(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": title, "maxResults": 1},
        timeout=8
    )
    if r.status_code != 200 or "items" not in r.json():
        return False
    hit_title = r.json()["items"][0]["volumeInfo"].get("title", "")
    score = fuzz.token_set_ratio(_clean(title), _clean(hit_title)) / 100
    return score >= OPENALEX_TOLERANCE


def extract_year(cite: str) -> str | None:
    m = re.search(r"\((\d{4})\)", cite)
    return m.group(1) if m else None

def extract_authors(cite: str) -> list[str]:
    # Extract authors before the year
    m = re.match(r"^(.*)\(\d{4}\)", cite)
    if not m:
        return []
    authors_part = m.group(1)
    # Split on commas and ampersands, remove initials
    authors = re.split(r",|&", authors_part)
    # Keep only last names (first word before comma or ampersand)
    return [a.strip().split()[0] for a in authors if a.strip()]

def validate_citation(cite: str) -> str:
    cite  = unicodedata.normalize("NFKD", cite).strip().lstrip('"' "'" "•–—- ")
    m = title_re.search(cite)
    if m:
        title = m.group(1).strip()
    else:
        title = (re.match(r"(.+)", cite)).group(1).strip()
    year = extract_year(cite)
    cited_authors = extract_authors(cite)
    if doi_match := doi_re.search(cite):
        doi = doi_match.group(0)
        r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=8)
        if r.status_code == 200:
            msg = r.json()["message"]
            real_title = msg.get("title", [""])[0]
            real_year = str(msg.get("issued", {}).get("date-parts", [[None]])[0][0])
            real_authors = [a.get("family", "") for a in msg.get("author", []) if "family" in a]
            # Fuzzy title match
            title_score = fuzz.token_set_ratio(_clean(real_title), _clean(title)) / 100
            # Year match
            year_match = (year == real_year)
            # At least one author last name matches (case-insensitive)
            author_match = any(
                ca.lower() == ra.lower()
                for ca in cited_authors for ra in real_authors
            )
            print(f"[DEBUG] Title score: {title_score}, Year: {year} vs {real_year}, Author match: {author_match}")
            if title_score >= CROSSREF_TOLERANCE and year_match and author_match:
                return "valid"
            else:
                return "metadata_error"
        else:
            return "not_found"
    # No DOI: fallback to OpenAlex/Google Books as before
    if _openalex_ok(title):
        return "valid"
    if google_books_ok(title):
        return "valid"
    return "not_found"
    
# --------------------------------------------------------------------
# Step 2 – Batch validate entire log
# --------------------------------------------------------------------

def batch_validate() -> None:
    if not CSV_PATH.exists():
        print("[validate] no output.csv yet – skip.")
        return

    df = pd.read_csv(CSV_PATH, engine="python", quoting=csv.QUOTE_ALL, on_bad_lines="skip", encoding="utf-8-sig")

    # rebuild header if lost
    if {"role", "content"}.issubset(df.columns) is False and len(df.columns) >= 5:
        df.columns = ["timestamp", "thread_id", "run_id", "role", "content"][: len(df.columns)]

    rows: list[dict] = []
    for _, r in df.iterrows():
        if str(r.get("role", "")).strip(' "').lower() != "assistant":
            continue
        content = str(r.get("content", ""))
        content = content.replace("\\n", "\n").strip()
        citations = re.split(r"\n{2,}", content)
        for raw in citations:
            # Remove leading number and period (e.g., "1. "), or dash and space ("- ")
            raw = re.sub(r"^\s*(\d+\.\s*|- )", "", raw).strip()
            if len(raw) < 10:
                continue
            rows.append({
                "thread_id": r.get("thread_id", ""),
                "citation":  raw,
            })

    print(f"[debug] extracted {len(rows)} citation lines")
    if not rows:
        print("[validate] no citation lines found.")
        return

    results = []
    for i, row in enumerate(rows, 1):
        row["status"] = validate_citation(row["citation"])
        results.append(row)
        if i % RATE_LIMIT_PER_S == 0:
            time.sleep(3)

    pd.DataFrame(results).to_csv(OUT_PATH, index=False, quoting=csv.QUOTE_ALL)
    print(f"[validate] wrote {len(results)} rows → {OUT_PATH}")

# --------------------------------------------------------------------
# Demo run when executed directly
# --------------------------------------------------------------------
if __name__ == "__main__":
    # Load all prompts from input.csv
    input_path = DATA_DIR / "input.csv"
    prompts = pd.read_csv(input_path, header=None, encoding="utf-8-sig")[0].tolist()

    for idx, prompt in enumerate(prompts, 1):
        print(f"\n[run] Prompt {idx}/{len(prompts)}")
        for i in range(45):
            print(f"  [subrun] {i+1}/45")
            log_single_prompt(prompt, temperature=0.7)
            # Optionally, sleep a bit to avoid rate limits
            #time.sleep(1)
    # Only validate once, after all prompts are done
    batch_validate()
