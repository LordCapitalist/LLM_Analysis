import pandas as pd
import re
from rapidfuzz import fuzz
import pathlib

DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"

# Load your manual check results
checked = pd.read_csv(DATA_DIR / "compact_nonvalid_titles.csv", quoting=1, on_bad_lines="skip", encoding="utf-8-sig", engine="python")
# Load your original validated output
df = pd.read_csv(DATA_DIR / "validated_output.csv")

# Extract title from each citation (same as before)
def extract_title(citation):
    m = re.search(r"\(\d{4}\)\.\s*(.+?)\.", str(citation))
    return m.group(1).strip() if m else str(citation)[:80]
df["title"] = df["citation"].apply(extract_title)

# For each citation, fuzzy match to checked titles and assign 'real' status
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

# Count not real per thread_id
not_real_counts = df[df["manual_real"] == "not real"].groupby("thread_id").size().reset_index(name='count')
not_real_counts = not_real_counts.sort_values(by='count', ascending=False)

# Load prompts
prompts = pd.read_csv(DATA_DIR / "input.csv", header=None, encoding="utf-8-sig")[0].tolist()

# Map each thread_id to its prompt by first occurrence order
thread_to_prompt = {}
thread_order = []
for _, row in df.iterrows():
    tid = row["thread_id"]
    if tid not in thread_to_prompt:
        thread_order.append(tid)
        thread_to_prompt[tid] = None  # placeholder

for idx, tid in enumerate(thread_order):
    if idx < len(prompts):
        thread_to_prompt[tid] = prompts[idx]
    else:
        thread_to_prompt[tid] = "(prompt not found)"

# Add prompt column to not_real_counts
not_real_counts["prompt"] = not_real_counts["thread_id"].map(thread_to_prompt)

# Show the top threads with their prompts and fake count
print("Threads with most 'not real' citations and their prompts:\n")
for _, row in not_real_counts.iterrows():
    print(f"Thread ID: {row['thread_id']}")
    print(f"Fake count: {row['count']}")
    print(f"Prompt:\n{row['prompt']}\n{'-'*60}")

# Optionally, save to CSV for review
not_real_counts.to_csv(DATA_DIR / "not_real_threads_with_prompts.csv", index=False)