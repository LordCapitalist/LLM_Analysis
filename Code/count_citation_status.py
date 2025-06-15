import pandas as pd
import pathlib
from rapidfuzz import fuzz, process
import re

BASE_DIR  = pathlib.Path(__file__).resolve().parent
DATA_DIR  = BASE_DIR / "Data"
OUT_PATH  = DATA_DIR / "validated_output.csv"

# Load the validated output
df = pd.read_csv(OUT_PATH, quoting=1)

# Only non-valid citations
non_valid = df[df["status"] != "valid"].copy()

# Extract title using regex (APA: after year, before next period)
def extract_title(citation):
    m = re.search(r"\(\d{4}\)\.\s*(.+?)\.", citation)
    return m.group(1).strip() if m else citation[:80]

non_valid["title"] = non_valid["citation"].apply(extract_title)

# Fuzzy group titles
groups = []
used = set()
titles = non_valid["title"].tolist()
for i, t in enumerate(titles):
    if i in used:
        continue
    group = [i]
    for j in range(i+1, len(titles)):
        if j in used:
            continue
        if fuzz.token_set_ratio(t, titles[j]) > 80:
            group.append(j)
            used.add(j)
    groups.append(group)

# Summarize
print("Fuzzy grouped non-valid citations:")
for group in groups:
    count = non_valid.iloc[group].shape[0]
    statuses = non_valid.iloc[group]["status"].value_counts().to_dict()
    print(f"\nCount: {count} | Statuses: {statuses}")
    print("Example citation:", non_valid.iloc[group[0]]["citation"])
    if len(group) > 1:
        print("Grouped with:")
        for idx in group[1:]:
            print("  -", non_valid.iloc[idx]["citation"])

# Optionally, save a summary CSV
summary = []
for group in groups:
    row = non_valid.iloc[group[0]].to_dict()
    row["fuzzy_count"] = len(group)
    row["statuses"] = non_valid.iloc[group]["status"].value_counts().to_dict()
    summary.append(row)
pd.DataFrame(summary).to_csv(DATA_DIR / "fuzzy_non_valid_summary.csv", index=False, quoting=1)