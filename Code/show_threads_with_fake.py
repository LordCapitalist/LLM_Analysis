import pandas as pd
import pathlib

DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"

# Load not real counts per thread
not_real_counts = pd.read_csv(DATA_DIR / "not_real_per_thread.csv")
not_real_counts = not_real_counts.rename(columns={not_real_counts.columns[0]: "thread_id", not_real_counts.columns[1]: "count"})

# Load prompts
prompts = pd.read_csv(DATA_DIR / "input.csv", header=None, encoding="utf-8-sig")[0].tolist()

def thread_to_index(thread_id):
    # Extract the thread index from thread_id (assuming order matches input.csv)
    # If thread_id is like 'thread_xxxxx', get its order in validated_output.csv
    # Otherwise, just enumerate
    return None  # You may need to map this based on your actual logic

# If you have a mapping from thread_id to prompt index, use it here.
# Otherwise, if thread_ids are in order, you can just enumerate:
thread_id_to_prompt = {}
for idx, prompt in enumerate(prompts):
    # If your thread_ids are in the same order as prompts, this works:
    thread_id_to_prompt[idx] = prompt

# Try to match thread_id to prompt index (if possible)
print("Threads with most 'not real' citations and their prompts:\n")
for i, row in not_real_counts.iterrows():
    thread_id = row["thread_id"]
    count = row["count"]
    # Try to extract index from thread_id if possible
    # If thread_id is like 'thread_0', 'thread_1', etc.:
    idx = None
    if thread_id.startswith("thread_"):
        try:
            idx = int(thread_id.split("_")[1], 36)  # If base36, else just int()
        except Exception:
            pass
    if idx is not None and idx < len(prompts):
        prompt = prompts[idx]
    else:
        prompt = "(prompt not found)"
    print(f"{thread_id} ({count} not real):\n{prompt}\n{'-'*60}")