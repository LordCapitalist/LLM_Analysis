import pandas as pd
import pathlib
from rapidfuzz import fuzz

DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"

# Load validated output with manual labels
df = pd.read_csv(DATA_DIR / "validated_output.csv")
# Load your manual check results (with 'real'/'not real' labels)
checked = pd.read_csv(DATA_DIR / "compact_nonvalid_titles.csv", quoting=1, on_bad_lines="skip", encoding="utf-8-sig", engine="python")
# Load prompts
prompts = pd.read_csv(DATA_DIR / "input.csv", header=None, encoding="utf-8-sig")[0].tolist()

# Extract title from each citation
import re
def extract_title(citation):
    m = re.search(r"\(\d{4}\)\.\s*(.+?)\.", str(citation))
    return m.group(1).strip() if m else str(citation)[:80]
df["title"] = df["citation"].apply(extract_title)

# Fuzzy match each citation to checked titles and assign 'real' status
def match_real_status(row):
    best = None
    best_score = 0
    for _, checked_row in checked.iterrows():
        checked_title = str(checked_row.get("title", ""))
        real_val = checked_row.get("real", "")
        if not isinstance(real_val, str):
            continue
        score = fuzz.token_set_ratio(row["title"], checked_title)
        if score > best_score and real_val.strip():
            best = real_val.strip().lower()
            best_score = score
    return best if best_score > 80 else None

df["manual_real"] = df.apply(match_real_status, axis=1)

# Count 'not real' per thread_id
not_real_counts = df[df["manual_real"] == "not real"].groupby("thread_id").size()

# Find the thread_id with the most 'not real'
if not not_real_counts.empty:
    max_thread = not_real_counts.idxmax()
    max_count = not_real_counts.max()
    # Map thread_id to prompt index (assuming order)
    thread_ids = df["thread_id"].unique().tolist()
    try:
        prompt_idx = thread_ids.index(max_thread)
        prompt_text = prompts[prompt_idx]
    except Exception:
        prompt_text = "(prompt not found)"
    print(f"Prompt with most 'not real' citations:\n")
    print(f"Thread ID: {max_thread}")
    print(f"Count: {max_count}")
    print(f"Prompt:\n{prompt_text}")
else:
    print("No 'not real' citations found.")