import pandas as pd
import pathlib
from collections import Counter

DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"
summary_path = DATA_DIR / "fuzzy_non_valid_summary.csv"

df = pd.read_csv(summary_path)

# Show only the most important columns for manual review
compact = df[["title", "fuzzy_count", "statuses"]].copy()
compact = compact.sort_values("fuzzy_count", ascending=False)

# Only show titles with more than 3 non-valid occurrences
print(compact[compact["fuzzy_count"] > 3].to_string(index=False))

# Save to a new CSV for easy searching/filtering
compact.to_csv(DATA_DIR / "compact_nonvalid_titles.csv", index=False)