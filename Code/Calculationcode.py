#%% #[1]This code calculates the amount of citations needed to achieve a precision of ±2 percentage points
#With a prior hallucination rate of 18% based on prior knowledge from Walter and Wilders report and a confidence level of 95%.
#Lastly it calculated how many times is needed per prompt, assuming 5 citations per prompt.
import math

def n_single_proportion(p: float, E: float, conf: float = 0.95) -> int:
    z = 1.96  #the z score for 95% confidence level is 1.96
    n = (z**2 * p * (1 - p)) / (E**2)
    return math.ceil(n)

# --- values --------------------------------------------------------
p = 0.18     # prior hallucination rate from the Walter and Wilder report
E = 0.02     # ±2 percentage-point precision
n_cite   = n_single_proportion(p, E)

# --- output --------------------------------------------------------
print(f"Required citations : {n_cite}")
print(f"Required amount of citations per prompt: {math.ceil(n_cite / 7)}")
print(f"Required amount of citations per prompt with 5 citations: {math.ceil(math.ceil(n_cite/7) / 5)}")




#%% #[2]This code was used to replicate the same style as in the validated_output.csv file, where all fields are quoted.
#This was used after manually checking through the validated_output and reassembling the missing values.
#Only run this code if wanting to create or recreate the testing
import pandas as pd
import pathlib
import os
# Loads the CSV files from the folders with pathlib
DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"
summary_path = DATA_DIR / "Missingdata/validated_output_with_missing_values.csv"
output_path = DATA_DIR / "Corrected_output"

# Loads the excel file with pandas
df = pd.read_csv(summary_path, sep=";", encoding="utf-8")
# Exports with all fields 
filename = "output_quoted2.csv"
os.makedirs(output_path, exist_ok=True)
#saves it in the corrected output folder
full_path = os.path.join(output_path, filename)
df.to_csv(full_path, index=False, quoting=1)


# %% #[3]This code was used to count how many citations had the status "valid","Metadata_error" and "not_found".
#which were used for further analysis. 
import pandas as pd
import pathlib
# Loads the CSV files with pathlib
DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"
summary_path = DATA_DIR / "Corrected_output/output_quoted.csv"

#Reads with pandas
df1 = pd.read_csv(summary_path)
print("Total citations:", df1.shape[0])

#prints the sums of each status
print((df1['status'] == 'valid').sum())
print((df1['status'] == "not_found").sum())
print((df1['status'] == "metadata_error").sum())
print((df1['status'] == 'valid').sum()+(df1['status'] == "not_found").sum()+(df1['status'] == "metadata_error").sum())

# %% #[4] This is the code which finds the citations which can be grouped together using a specified threshold. This one was used to create the "metadata_error"
#and "not_found" fuzz count.
# Only run this code if trying to create/replicate the testing
import pandas as pd
import pathlib
from rapidfuzz import fuzz, process
import re
#Use pathlib to access the folders
BASE_DIR  = pathlib.Path(__file__).resolve().parent
DATA_DIR  = BASE_DIR / "Data"
OUT_PATH  = DATA_DIR / "Corrected_output/output_quoted.csv"

# Load the validated output with pandas
df = pd.read_csv(OUT_PATH)

# Takes only the non-valid citations to be fuzzed.
non_valid = df[df["status"] != "valid"].copy()

# Extract title using regex (APA: after year, before next period) 
def extract_title(citation):
    m = re.search(r"\(\d{4}\)\.\s*(.+?)\.", citation)
    return m.group(1).strip() if m else citation[:80]

non_valid["title"] = non_valid["citation"].apply(extract_title)

# Group the citations by titles using Fuzz
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

# Prints the grouped titles in the terminal with their fuzz count
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

# And saves it to a .csv file for the compactvalidation script
summary = []
for group in groups:
    row = non_valid.iloc[group[0]].to_dict()
    row["fuzzy_count"] = len(group)
    row["statuses"] = non_valid.iloc[group]["status"].value_counts().to_dict()
    summary.append(row)
pd.DataFrame(summary).to_csv(DATA_DIR / "Grouped_validation/Fuzzygroups.csv", index=False, quoting=1)

# %% ##[5] Same as previus this one were made for the "valid" part and should not be run this cell only if creating a new test.
import pandas as pd
import pathlib
from rapidfuzz import fuzz, process
import re

BASE_DIR  = pathlib.Path(__file__).resolve().parent
DATA_DIR  = BASE_DIR / "Data"
OUT_PATH  = DATA_DIR / "Corrected_output/output_quoted.csv"

# Load the validated output
df = pd.read_csv(OUT_PATH)

# Only akte the valid citations
valid = df[df["status"] == "valid"].copy()

# Extract title using regex (APA: after year, before next period)
def extract_title(citation):
    m = re.search(r"\(\d{4}\)\.\s*(.+?)\.", citation)
    return m.group(1).strip() if m else citation[:80]

valid["title"] = valid["citation"].apply(extract_title)

# Fuzzy group titles
groups = []
used = set()
titles = valid["title"].tolist()
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

# Print again
print("Fuzzy grouped non-valid citations:")
for group in groups:
    count = valid.iloc[group].shape[0]
    statuses = valid.iloc[group]["status"].value_counts().to_dict()
    print(f"\nCount: {count} | Statuses: {statuses}")
    print("Example citation:", valid.iloc[group[0]]["citation"])
    if len(group) > 1:
        print("Grouped with:")
        for idx in group[1:]:
            print("  -", valid.iloc[idx]["citation"])

# Save as a .csv file again
summary = []
for group in groups:
    row = valid.iloc[group[0]].to_dict()
    row["fuzzy_count"] = len(group)
    row["statuses"] = valid.iloc[group]["status"].value_counts().to_dict()
    summary.append(row)
pd.DataFrame(summary).to_csv(DATA_DIR / "Grouped_validation/Fuzzygroups2.csv", index=False, quoting=1)

# %% ## [6]. This is the grouping script for the "metadata_error" and "not_found"
# Check the Compactvalidation.csv file for the manual review of the fuzzy groups
# Only run this script if wanting to create/reacreate the test !!!Warning!!! running this will remove the manually reviewed tags
import pandas as pd
import pathlib
from collections import Counter

#import the data using the pathlib
DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"
summary_path = DATA_DIR / "Grouped_validation/Fuzzygroups.csv"
#and againg read with panda
df = pd.read_csv(summary_path)

#compacts the fuzzy documents and
compact = df[["title", "fuzzy_count", "statuses"]].copy()
compact = compact.sort_values("fuzzy_count", ascending=False)

#print(compact[compact["fuzzy_count"] > 3].to_string(index=False))

# Save to a .csv for manual validation
compact.to_csv(DATA_DIR / "Grouped_validation/Compactvalidation.csv", index=False )

# %% ## [7]. This is the grouping script for the "valid"
# Check the Compactvalidation2.csv file for the manual review of the fuzzy groups
# Only run this script if wanting to create/reacreate the test !!!Warning!!! running this will remove the manually reviewed tags
import pandas as pd
import pathlib
from collections import Counter

DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"
summary_path = DATA_DIR / "Grouped_validation/Fuzzygroups2.csv"

df = pd.read_csv(summary_path)

compact = df[["title", "fuzzy_count", "statuses"]].copy()
compact = compact.sort_values("fuzzy_count", ascending=False)


# Save to a .csv for manual validation
compact.to_csv(DATA_DIR / "Grouped_validation/Compactvalidation2.csv", index=False , quoting=1)
# %% [8] This code is to see the sum of real and false citations in the compactvalidation.csv file.
# This is just the counting of which are tagged real or not real X(times) the amount of times the citation was grouped
import pandas as pd
import pathlib
DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"
another_path = DATA_DIR / "Grouped_validation/Compactvalidation.csv"
df = pd.read_csv(another_path)
realsum = 0
falsesum = 0

for index, row in df.iterrows():
    if row["real"]=="real":
        realsum += row["fuzzy_count"]
    elif row["real"]=="not real":
        falsesum += row["fuzzy_count"]

print(f"Total real citations: {realsum}")
print(f"Total not real citations: {falsesum}")
print(f"Total citations: {realsum + falsesum}")
print(f"Total citations: {falsesum/1575}")

# %% # %% [9] This code is to see the sum of real and false citations in the compactvalidation2.csv file.
# This is just the counting of which are tagged real or not real times the amount of times the citation was grouped. (Its the same as the one above :))
import pandas as pd
import pathlib
DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"
another_path = DATA_DIR / "Grouped_validation/Compactvalidation2.csv"
df = pd.read_csv(another_path)
realsum = 0
falsesum = 0

for index, row in df.iterrows():
    if row["real"]=="real":
        realsum += row["fuzzy_count"]
    elif row["real"]=="not real":
        falsesum += row["fuzzy_count"]

print(f"Total real citations: {realsum}")
print(f"Total not real citations: {falsesum}")
print(f"Total citations: {realsum + falsesum}")
print(f"Total citations: {falsesum/1575}")
# %% [10]. This is the confusion matrix based on running the two scripts above it is very possible to automate the process.
# Run this script to see the confusionmatrix. This is also calculating the recall, accuracy and precision of our validation script.
import numpy as np
import matplotlib.pyplot as plt
TP = 690  # True Positives
FN = 469  # False Negatives
FP = 90   # False Positives
TN = 322  # True Negatives
# Calculate precision and recall
precision = TP / (TP + FP) if (TP + FP) > 0 else 0
recall = TP / (TP + FN) if (TP + FN) > 0 else 0
Accuracy = (TP + TN) / 1571


cm = np.array([[690, 469],
               [90, 322]])

labels = ['Real', 'Not Real']

fig, ax = plt.subplots()
im = ax.imshow(cm, cmap='Blues')

# Add text annotations
for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        ax.text(j, i, cm[i, j], ha='center', va='center', color='black')

# Set tick labels
ax.set_xticks(np.arange(len(labels)))
ax.set_yticks(np.arange(len(labels)))
ax.set_xticklabels(labels)
ax.set_yticklabels(labels)

# Label axes
ax.set_xlabel('Predicted')
ax.set_ylabel('Actual')
plt.title('Confusion Matrix')
plt.colorbar(im)
plt.tight_layout()
plt.show()

print(f"Precision: {precision:.2f}")
print(f"Recall: {recall:.2f}")
print(f"Accuracy: {Accuracy:.2f}")

# %% [11] This is just a combination of the scripts [8] and [9] but to get the total amount of false and real citations.
import pandas as pd
import pathlib
DATA_DIR = pathlib.Path(__file__).resolve().parent / "Data"
another_path = DATA_DIR / "Grouped_validation/Compactvalidation.csv"
another_other_path = DATA_DIR / "Grouped_validation/Compactvalidation2.csv"
df = pd.read_csv(another_path)
df1 = pd.read_csv(another_other_path)

realsum1 = 0
falsesum1 = 0
realsum2 = 0
falsesum2 = 0

for index, row in df.iterrows():
    if row["real"]=="real":
        realsum1 += row["fuzzy_count"]
    elif row["real"]=="not real":
        falsesum1 += row["fuzzy_count"]

for index, row in df1.iterrows():
    if row["real"]=="real":
        realsum2 += row["fuzzy_count"]
    elif row["real"]=="not real":
        falsesum2 += row["fuzzy_count"]


print(f"Total real citations: {realsum1+realsum2}")
print(f"Total not real citations: {falsesum1+falsesum2}")
print(f"Total citations: {realsum1 + falsesum1+ realsum2 + falsesum2}")
print(f"Total citations: {(falsesum1+falsesum2)/1575}")
# %% [12] This script calculates the confidence interval of the false citation frequency. !!!"once again it could be automated"!!!.
import math

# Inputs
p = 0.26
n = 1575
z = 1.96  # z-score for 95% confidence

# Standard error
se = math.sqrt(p * (1 - p) / n)

# Confidence interval
ci_lower = p - z * se
ci_upper = p + z * se

print(f"95% Confidence Interval: [{ci_lower:.4f}, {ci_upper:.4f}]")


# %% [13] Lastly this a two proportion z_test from the statsmodel package to calculate if there is a significant statistical difference between the test outlined
# And the result from Walter and Wilder. 
import numpy as np
suc1 = 0.26158*1571
suc2 = 0.18 *636
count = np.array([suc1, suc2])

nobs = np.array([1571, 636])

# import package
import statsmodels.api as sm

# perform Two-proportion Z test package
stat, pval = sm.stats.proportions_ztest(count, nobs)

print(stat, pval)
