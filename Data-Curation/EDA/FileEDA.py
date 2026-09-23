import pandas as pd
import pyarrow.parquet as pq
from file_detector import FileDetector 

class FileEDA:
    def __init__(self, file_path):
        """
        Initialize the FileEDA class with the file path and a FileDetector instance.
        """
        self.file_path = file_path
        self.detector = FileDetector(file_path)
        self.file_type = self.detector.detect_file_type()

    def perform_eda(self):
        """
        Perform EDA based on the file type and size.
        """
        if self.file_type == "CSV":
            return self._eda_csv()
        elif self.file_type == "Parquet":
            return self._eda_parquet()
        elif self.file_type == "JSON":
            return self._eda_json()
        else:
            raise ValueError("Unsupported file type for EDA.")

    def _eda_csv(self):
        """
        Perform EDA for CSV files.
        """
        if self.detector.is_large_file():
            chunks = pd.read_csv(self.file_path, chunksize=100000)
            for i, chunk in enumerate(chunks):
                print(f"Chunk {i+1} Summary Statistics:")
                print(chunk.describe())
        else:
            df = pd.read_csv(self.file_path)
            print("Schema:")
            print(df.info())
            print("Summary Statistics:")
            print(df.describe())
            print("Missing Values:")
            print(df.isnull().sum())
        return "EDA for CSV completed."

    def _eda_parquet(self):
        """
        Perform EDA for Parquet files.
        """
        if self.detector.is_large_file():
            print("Parquet file is large. Consider using Dask or DuckDB for distributed processing.")
        else:
            table = pq.read_table(self.file_path)
            print("Schema:")
            print(table.schema)
            df = pd.read_parquet(self.file_path)
            print("Summary Statistics:")
            print(df.describe())
            print("Missing Values:")
            print(df.isnull().sum())
        return "EDA for Parquet completed."

    def _eda_json(self):
        """
        Perform EDA for JSON files.
        """
        df = pd.read_json(self.file_path, lines=True)  # Assuming line-delimited JSON
        print("Schema:")
        print(df.info())
        print("Summary Statistics:")
        print(df.describe())
        print("Missing Values:")
        print(df.isnull().sum())
        return "EDA for JSON completed."


if __name__ == "__main__":
    file_path = "/Users/coffeer/Desktop/EDA/dataset /df_3yr_fn1.csv"
    eda = FileEDA(file_path)
    result = eda.perform_eda()
    print(result)
