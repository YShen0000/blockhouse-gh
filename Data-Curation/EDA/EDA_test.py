import unittest
from FileEDA import FileEDA

class TestFileEDA(unittest.TestCase):

    def setUp(self):
        """
        Setup paths for the existing dataset files.
        """
        self.csv_file = "/Users/coffeer/Desktop/EDA/dataset /df_3yr_fn1.csv"
        self.parquet_file = "/Users/coffeer/Desktop/EDA/dataset /merged_dw_clob.parquet"

    def test_perform_eda_csv(self):
        """
        Test EDA process for CSV files.
        """
        eda_csv = FileEDA(self.csv_file)
        result = eda_csv.perform_eda()
        self.assertEqual(result, "EDA for CSV completed.")
    
    def test_perform_eda_parquet(self):
        """
        Test EDA process for Parquet files.
        """
        eda_parquet = FileEDA(self.parquet_file)
        result = eda_parquet.perform_eda()
        self.assertEqual(result, "EDA for Parquet completed.")

if __name__ == '__main__':
    unittest.main()
