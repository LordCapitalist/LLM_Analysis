"""
Citation validation script for the report "EVALUATION OF LARGE LANGUAGE MODELS:CITATION HALLUCINATION"
______________________________________________________________________________________________________
Credit: See the credits in the read.me file
_______________________________________________________________________________________________________
Layout of everything before the code
-Imports
-Global variables
-File Locations
-API-Endpoint
-(For the Windows Users)
-Helper
Layout of the code
-Step 1: Send prompts to the GPT-4o model
-Step 2: Validationmethods setup
-Step 3: Extract authors and year
-Step 4: Validation_citation script
-Step 5: Batch validation and running the script
"""

# --------------------------------------------------------------------
# Imports
# --------------------------------------------------------------------
import pathlib, re, csv, time, unicodedata, requests
from datetime import datetime
import pandas as pd
from rapidfuzz import fuzz
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
import ctypes
# --------------------------------------------------------------------
# Global variable
# --------------------------------------------------------------------
CROSSREF_TOLERANCE = 0.65  # This is the tolarance applied to the crossref function which checks if the DOI is real
OPENALEX_TOLERANCE = 0.70 #This is the tolarance applied to the OpenAlex function, and also the Google Books function which the
#falls back on if the crossref fails
RATE_LIMIT_PER_S   = 3  # polite API throttle

# --------------------------------------------------------------------
# File Locations
# --------------------------------------------------------------------
BASE_DIR  = pathlib.Path(__file__).resolve().parent
DATA_DIR  = BASE_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH  = DATA_DIR / "Rawdata/output.csv" #This where the content of the prompts is outputted to
OUT_PATH  = DATA_DIR / "Rawdataa/validated_output.csv" #And this is where the content of validating the output is placed.

# --------------------------------------------------------------------
# API-Endpoint
# --------------------------------------------------------------------
ENDPOINT        = "https://project-02445.services.ai.azure.com/api/projects/project-02445" #If you want to create/recreate the test please remove the endpoint
#and replace with your own
DEPLOYMENT_NAME = "gpt-4o"  # What the AI-agent should be deployed as

# --------------------------------------------------------------------
# (For the Windows Users)
# --------------------------------------------------------------------
# Prevent Windows from sleeping while script runs, which it can take quite a while collecting and validating
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

# --------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------
def is_citation_line(raw: str) -> bool: #this was created as a simple helper since without it sometimes the citations would not be detected
    return bool(raw.strip())

# --------------------------------------------------------------------
# Step 1 – Send the prompts to the GPT-4o model
# --------------------------------------------------------------------
def log_single_prompt(prompt: str, temperature: float = 0.7) -> None: #Temperature is included here so it can be used in the create agent statement
    """Send *prompt* to GPT‑4o; append assistant message to output.csv."""
    client  = AIProjectClient(endpoint=ENDPOINT, credential=DefaultAzureCredential())

    agent = client.agents.create_agent(
        model=DEPLOYMENT_NAME,
        name="citation-agent", #This is irrelevant since it would be deleted once the current prompt is recieved.
        #The system instructions as outlined in the report
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
        temperature=temperature, #The temperature to match the normal GPT-4o 0.7 temperature
    )

    thread = client.agents.threads.create() #create a thread on a new agent
    client.agents.messages.create(thread_id=thread.id, role="user", content=prompt) #create a new message to the agent

    run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id) #Then create and process the run and see if it actually rund
    if run.status == "failed":
        raise RuntimeError(run.last_error)

    msgs = client.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING) #listing the msgs from the agent so the 5 citations
 
    records = [{
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "thread_id": thread.id,
        "run_id"   : run.id,
        "role"     : m.role,
        "content"  : m.text_messages[-1].text.value,
    } for m in msgs if m.run_id == run.id and m.text_messages] #recording the which then is outputted into the output.csv

    pd.DataFrame(records).to_csv(
        CSV_PATH,
        mode="a",
        header=not CSV_PATH.exists(),
        index=False,
        quoting=csv.QUOTE_ALL,
    ) #Which is done right here
    print(f"[log] added {len(records)} assistant row → {CSV_PATH}") 
    client.agents.delete_agent(agent.id)# Finally deleting the agent

# --------------------------------------------------------------------
# Step 2 Validationmethods setup
# --------------------------------------------------------------------

doi_re   = re.compile(r"10\.\d{4,9}/[\w.\-()/]+", re.I) #These two tries to compile the DOI (Digital object identifier) and the title into searchable objects
title_re = re.compile(r"\(\d{4}\)\.\s*(.+?)\.", re.S)


def _clean(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt).lower()
    txt = re.sub(r"[^a-z0-9\- ]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip() #This treis to clean up most of the citation to possibly be able to validate it. This introduced some error but since we 
#Manually validate in the end it won't create too much of a difference.

#______________________________________________________________________________________________________This was the original method but was refined into the validate_citation function (i left the comments in for understanding)
#def _crossref_ok(doi: str, cited_title: str) -> bool: #Credit to the crossref documentation which helped me construct this very ugly checker
    #r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=8) #The timeout is used as to not overload the api
    #it is not recommended to change since that could result in removed access to the API.
    #if r.status_code == 200:
        #real_title = r.json()["message"].get("title", [""])[0]
        #if real_title:                                   
            #score = fuzz.token_set_ratio(_clean(real_title), _clean(cited_title))/100
            #return score >= 0.80 #If the fuzzscore is not over 80% it will fallback to a simple DOI resolve check, which just means does the DOI connect to a site.
        #Doesnt matter which site it just checks if it at all connects to any site
    #return requests.head(f"https://doi.org/{doi}", allow_redirects=True, timeout=6).status_code == 200 #Again using a timeout this time a little lower since it should
    #Not normally end in the fallback
#________________________________________________________________________________________________________

def _openalex_ok(title: str) -> bool: #Credit tot he openalex documentation it was possible to create a very similar validation checker 
    r = requests.get("https://api.openalex.org/works", params={"search": title, "per_page": 1}, timeout=8) #A timeout again not to overload the API
    if r.status_code != 200 or r.json()["meta"].get("count", 0) == 0: #If the request to the api fails or there is nothing on the page the validation fails.
        #The json[""] simply means is there any json objects on the cite if not then it fails.
        return False
    hit_title = r.json()["results"][0]["title"] #If it actually finds somcething if would get the title and then using the fuzz as before see if its above the tolerance level
    score = fuzz.token_set_ratio(_clean(title), _clean(hit_title))/100
    return score >= OPENALEX_TOLERANCE


def google_books_ok(title: str) -> bool: #This is very similar to the openalex we simply test if the result acutally return something and if not we return false
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
# --------------------------------------------------------------------
# Step 3 Extract author and year
# --------------------------------------------------------------------
def extract_year(cite: str) -> str | None: #This is the two method we use to check whether the author and year is actually the real author and the real year
    m = re.search(r"\((\d{4})\)", cite)
    return m.group(1) if m else None

def extract_authors(cite: str) -> list[str]:# Following the APA structure the authors would always be before the year therefore the authors need to me extracted before the year
    m = re.match(r"^(.*)\(\d{4}\)", cite)
    if not m:
        return []
    authors_part = m.group(1)
    authors = re.split(r",|&", authors_part)    # Here we split on , and & since that is the mostly like defining seperator between multiple authors
    return [a.strip().split()[0] for a in authors if a.strip()]

# --------------------------------------------------------------------
# Step 4 validate_citation script
# --------------------------------------------------------------------
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
# Step 5 – Batch validate and run the script
# --------------------------------------------------------------------

def batch_validate() -> None: #We basically now just run through the entire output.csv file and validate with the validatecitation script
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

if __name__ == "__main__":
    input_path = DATA_DIR / "input.csv" #Here we load all the prompts in from the imputfile can be replaced
    prompts = pd.read_csv(input_path, header=None, encoding="utf-8-sig")[0].tolist()
    for idx, prompt in enumerate(prompts, 1):
        print(f"\n[run] Prompt {idx}/{len(prompts)}")
        for i in range(45):
            print(f"  [subrun] {i+1}/45")
            log_single_prompt(prompt, temperature=0.7) 
    # Only validate once, after all prompts are done
    batch_validate()
    print("\n[done] All prompts logged and validated.")