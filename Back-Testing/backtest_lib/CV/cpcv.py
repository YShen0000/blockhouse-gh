from itertools import combinations
import numpy as np

class CPCV:
    def __init__(self, n_splits=5, n_combinations=3, purge_gap=1):
        self.n_splits = n_splits
        self.n_combinations = n_combinations
        self.purge_gap = purge_gap

    def split(self, X, y=None):
        """
        Combines different fold sets, creating train-test pairs with purging.
        """
        n_samples = len(X)
        fold_size = n_samples // self.n_splits
        indices = np.arange(n_samples)
        fold_indices = [indices[i * fold_size:(i + 1) * fold_size] for i in range(self.n_splits)]

        for combination in combinations(range(self.n_splits), self.n_combinations):
            train_indices = np.hstack([fold_indices[i] for i in range(self.n_splits) if i not in combination])
            test_indices = np.hstack([fold_indices[i] for i in combination])

            # Apply purging by removing the overlap between train and test sets
            purge_start = test_indices[0] - self.purge_gap if test_indices[0] - self.purge_gap > 0 else 0
            train_indices = train_indices[train_indices > purge_start]

            yield train_indices, test_indices

class PurgedKFoldCV:
    def __init__(self, n_splits=5, purge_gap=1):
        self.n_splits = n_splits
        self.purge_gap = purge_gap

    def split(self, X, y=None):
        """
        Generates indices for training and testing sets while ensuring no leakage (purging).
        """
        n_samples = len(X)
        fold_size = n_samples // self.n_splits

        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = test_start + fold_size

            # Apply purging by skipping a few samples between train and test sets
            train_indices = np.concatenate((
                np.arange(0, test_start - self.purge_gap),
                np.arange(test_end + self.purge_gap, n_samples)
            ))

            test_indices = np.arange(test_start, test_end)

            yield train_indices, test_indices

# import pandas as pd
# from itertools import combinations
# import numpy as np

# Assuming CPCV is already implemented as above

# Load your CSV file
# df = pd.read_csv(r'C:\Users\Naitik\blockhouse\Blockhouse-ML\BacktestData\AAPL_2024-09-09.csv')

# Assuming your time column is named 'time' and is in a format like 'HH:MM'
# df['time'] = pd.to_datetime(df['time'])  # Convert time column to datetime




# # Instantiate the CPCV object
# cpcv = CPCV(n_splits=5, n_combinations=3, purge_gap=1)

# # Split the data using CPCV
# for train_idx, test_idx in cpcv.split(df):
#     X_train, X_test = df.iloc[train_idx], df.iloc[test_idx]
#     X_train = df.iloc[train_idx]
#     X_test = df.iloc[test_idx]
#     # You can now use X_train and X_test for your model training and backtesting
#     # print("Train indices:", train_idx)
#     # print("Test indices:", test_idx)
#     print(X_train,'train')
#     print(X_test, 'test')

#for Kfold
# pkf_cv = PurgedKFoldCV(n_splits=5, purge_gap=1)

# # Split the data and print train and test sets
# for train_idx, test_idx in pkf_cv.split(df):
#     X_train = df.iloc[train_idx]
#     X_test = df.iloc[test_idx]

#     print("\nTrain Data:")
#     print(X_train)
#     print("\nTest Data:")
#     print(X_test)
#     print("\nTrain Indices:", train_idx)
#     print("Test Indices:", test_idx)