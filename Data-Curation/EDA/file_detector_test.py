import unittest
from file_detector import FileDetector

class TestFileDetector(unittest.TestCase):

    def setUp(self):
        """
        Setup paths for the existing dataset files.
        """
        self.csv_file = "/Users/coffeer/Desktop/EDA/dataset /df_3yr_fn1.csv"
        self.parquet_file =  "/Users/coffeer/Desktop/EDA/dataset /merged_dw_clob.parquet"

    def test_detect_file_type(self):
        """
        Test detection of file types.
        """
        detector_csv = FileDetector(self.csv_file)
        self.assertEqual(detector_csv.detect_file_type(), "CSV")
        
        detector_parquet = FileDetector(self.parquet_file)
        self.assertEqual(detector_parquet.detect_file_type(), "Parquet")
    
    def test_is_large_file(self):
        """
        Test file size classification.
        """
        detector_csv = FileDetector(self.csv_file)
        self.assertFalse(detector_csv.is_large_file(threshold_mb=100))  # Small CSV file
        
        detector_parquet = FileDetector(self.parquet_file)
        self.assertTrue(detector_parquet.is_large_file(threshold_mb=100))  # Large Parquet file
    
    def test_determine_analysis_tool(self):
        """
        Test determination of analysis tools based on file type and size.
        """
        detector_csv = FileDetector(self.csv_file)
        self.assertEqual(detector_csv.determine_analysis_tool(), "Use Pandas for CSV")
        
        detector_parquet = FileDetector(self.parquet_file)
        self.assertEqual(detector_parquet.determine_analysis_tool(), "Use Dask or DuckDB for Parquet")

if __name__ == '__main__':
    unittest.main()
