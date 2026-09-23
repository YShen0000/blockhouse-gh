import os

class FileDetector:
    def __init__(self, file_path):
        """
        Initialize the FileDetector with a file path.
        """
        self.file_path = file_path
        self.file_type = None
        self.is_large = None

    def detect_file_type(self):
        """
        Detect the file type based on its extension.
        """
        _, file_extension = os.path.splitext(self.file_path)
        file_extension = file_extension.lower()
        
        if file_extension in ['.csv']:
            self.file_type = "CSV"
        elif file_extension in ['.parquet']:
            self.file_type = "Parquet"
        elif file_extension in ['.json']:
            self.file_type = "JSON"
        else:
            self.file_type = "Unknown"
        return self.file_type

    def is_large_file(self, threshold_mb=100):
        """
        Determine if a file is large based on its size in MB.
        """
        file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)  # Convert bytes to MB
        self.is_large = file_size_mb > threshold_mb
        return self.is_large

    def determine_analysis_tool(self):
        """
        Determine the appropriate tool for analysis based on file type and size.
        """
        if self.file_type is None:
            self.detect_file_type()
        
        if self.file_type == "CSV":
            return "Use Dask for CSV" if self.is_large_file() else "Use Pandas for CSV"
        elif self.file_type == "Parquet":
            return "Use Dask or DuckDB for Parquet" if self.is_large_file() else "Use Pandas or PyArrow for Parquet"
        elif self.file_type == "JSON":
            return "Use Pandas for JSON"
        else:
            return "Unsupported file type"

    def summary(self):
        """
        Provide a summary of the file's type and size classification.
        """
        return {
            "file_path": self.file_path,
            "file_type": self.file_type or self.detect_file_type(),
            "is_large": self.is_large if self.is_large is not None else self.is_large_file(),
            "analysis_tool": self.determine_analysis_tool()
        }

# Example Usage
if __name__ == "__main__":
    file_path = "/Users/coffeer/Desktop/EDA/dataset /df_3yr_fn1.csv"
    detector = FileDetector(file_path)
    print("File Type:", detector.detect_file_type())
    print("Is Large File:", detector.is_large_file())
    print("Recommended Tool:", detector.determine_analysis_tool())
    print("Summary:", detector.summary())
