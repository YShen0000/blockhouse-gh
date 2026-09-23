Here is an expanded **Markdown documentation** with a detailed explanation of each step performed by the scripts:

---

# Dataset Cleaning Process (dwas and match)

---

## Steps Performed

### 1. Split Data into Symbols

The script `split-data-to-symbols.py` processes the original raw dataset and organizes it by splitting the data into smaller symbol-specific files.

**Details**:

- **Input**: A single raw dataset file (e.g., CSV or similar) containing multiple records with a column representing **symbols**.
- **Process**:
  - The script reads the input dataset.
  - It identifies unique symbols from the dataset (e.g., column `symbol` or similar).
  - For each unique symbol:
    - Filters all rows corresponding to that symbol.
    - Saves the filtered data into a separate file (e.g., `symbol_A.csv`, `symbol_B.csv`).
- **Output**: A directory containing individual symbol-specific files, where each file contains data filtered for one symbol.

**Purpose**: Splitting data simplifies processing, enabling symbol-level operations and cleaning.

---

### 2. Merge Symbol Data Individually

The script `merge-symbol-data.py` takes the symbol-specific files (generated in Step 1) and combines them into a single, unified dataset.

**Details**:

- **Input**: A directory containing symbol-specific files (e.g., `symbol_A.csv`, `symbol_B.csv`).
- **Process**:
  - Reads all symbol files from the specified directory.
  - Ensures column consistency across all files (e.g., column headers match).
  - Concatenates the data from all symbol files into a single **merged dataset**.
  - Handles potential errors like:
    - Missing or misaligned columns.
    - Duplicate records (if applicable).
- **Output**: A single **merged_symbols.csv** file containing all symbol data in a consolidated format.

**Purpose**: Merging enables unified processing and ensures that all symbol data is ready for centralized cleaning.

---

### 3. Data Cleaning as Requested by the Strat-Dev Team

The script `data-cleaning.py` takes the merged dataset from Step 2 and applies a series of data cleaning operations based on requirements from the strat-dev team.

**Details**:

- **Input**: The merged dataset file (e.g., `merged_symbols.csv`).
- **Process**:
  - **Handling Missing Values**:
    - Identifies columns with missing or invalid data.
    - Fills missing values with appropriate strategies (e.g., mean, median, or placeholders) or removes rows/columns as necessary.
  - **Removing Duplicates**:
    - Detects and removes duplicate rows to avoid redundancy.
  - **Formatting Columns**:
    - Ensures all columns follow a consistent format (e.g., date formats, numeric precision, proper casing for string fields).
  - **Filtering Invalid Records**:
    - Removes rows with invalid or out-of-range data (e.g., negative values in a positive-only column).
  - **Custom Cleaning**:
    - Applies any additional transformations or filtering logic specifically requested by the strat-dev team.
- **Output**: A clean and structured dataset file (e.g., `cleaned_data.csv`).

**Purpose**: The cleaned dataset is now free of errors, duplicates, and inconsistencies, making it ready for downstream use in analysis, modeling, or reporting.

---
