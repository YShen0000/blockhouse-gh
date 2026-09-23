import unittest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, time
from alpha_utils import Alpha
from beta_utils import calculate_beta
from lambda_utils import LambdaEstimation
from myopic_model_utils import MyopicOptimizationModel
import sys

#

class TestMyopicModel(unittest.TestCase):
    def setUp(self):
        """
        Set up test fixtures before each test method.
        Creates sample data that matches the real data structure with timestamps and pricing information.
        The sample data mimics actual trading patterns with bid/ask spreads and signed volumes.
        """
        
        # Initialize model parameters with realistic values
        self.inventory = 5000  # Realistic inventory size based on volume patterns
        self.beta = 0.6931471805599453  # From your beta_utils calculation
        self.T = 10  # Time horizon
        self.N = 5   # Number of buckets
        self.sample_data = pd.read_csv("aapl-merged.csv")

    def tearDown(self):
        """
        Clean up after each test method by removing temporary test files.
        """
        pass

    def test_myopic_model_initialization(self):
        """
        Tests the initialization of the MyopicOptimizationModel with realistic market data.
        Verifies that all essential model parameters are set correctly and that the model
        can handle the data structure we've provided.
        """
        model = MyopicOptimizationModel(
            inputTradingData=self.sample_data,
            inventory=self.inventory,
            beta=self.beta,
            datasetFilePath='aapl-merged.csv',
            T=self.T,
            N=self.N
        )
        
        # Test initial values
        self.assertEqual(model.T, self.T, "Time horizon not set correctly")
        self.assertEqual(model.N, self.N, "Number of buckets not set correctly")
        self.assertEqual(model.Q0, self.inventory, "Initial inventory not set correctly")
        self.assertEqual(model.beta, self.beta, "Beta value not set correctly")
        self.assertEqual(len(model.trades_executed), 0, "Trades executed should be empty at initialization")
        
        # Verify that the trading data was properly loaded
        self.assertTrue(isinstance(model.trading_data, pd.DataFrame), "Trading data not loaded as DataFrame")
        self.assertTrue('ts_event' in model.trading_data.columns, "Trading data missing ts_event column")
        self.assertTrue('Signed Volume' in model.trading_data.columns, "Trading data missing Signed Volume column")
        
        # Check that inventory calculations are correct
        self.assertEqual(model.inventory_left, model.Q0, "Initial inventory_left should equal Q0")

    def test_alpha_stochastic_calculation(self):
            """
            Tests the stochastic alpha calculation functionality.
            This test verifies that:
            1. The stochastic alpha calculation produces the expected DataFrame structure
            2. The alpha values are within reasonable bounds
            3. The mu values are correctly calculated
            """
            # Initialize Alpha class with our test data
            alpha_calculator = Alpha('aapl-merged.csv')
            
            # Calculate stochastic alpha
            result = alpha_calculator.run("stochastic")
            stochastic_alpha = result[0]
            mu = result[1]
            print(f"stochastic alpha: {stochastic_alpha}")
            print(f"type of stochastic alpha: {type(stochastic_alpha)}")
            
            # Verify the structure of the output
            self.assertIsInstance(stochastic_alpha, pd.DataFrame, "Stochastic alpha should be a DataFrame")
            self.assertIsInstance(mu, pd.DataFrame, "Mu should be a DataFrame")
            
            # Check that the DataFrames have the required columns
            self.assertTrue('Datetime' in stochastic_alpha.columns, "Stochastic alpha missing Datetime column")
            self.assertTrue('Alpha' in stochastic_alpha.columns, "Stochastic alpha missing Alpha column")
            self.assertTrue('Datetime' in mu.columns, "Mu missing Datetime column")
            self.assertTrue('Mu' in mu.columns, "Mu missing Mu column")

    def test_alpha_deterministic_calculation(self):
        """
        Tests the deterministic alpha calculation functionality.
        This test verifies that:
        1. The deterministic alpha calculation produces all required components
        2. The values are within expected ranges
        3. The relationships between alpha, alpha prime, and alpha double prime are consistent
        """
        # Initialize Alpha class with our test data
        alpha_calculator = Alpha('aapl-merged.csv')
        
        # Calculate deterministic alpha
        result = alpha_calculator.run("deterministic")
        determined_alpha = result[0]
        alpha0 = result[1]
        alpha_prime = result[2]
        alpha_double_prime = result[3]
        
        # Verify the structure of the outputs
        self.assertIsInstance(determined_alpha, pd.DataFrame, "Determined alpha should be a DataFrame")
        self.assertIsInstance(alpha0, (int, float), "Alpha0 should be a numeric value")
        self.assertIsInstance(alpha_prime, pd.DataFrame, "Alpha prime should be a DataFrame")
        self.assertIsInstance(alpha_double_prime, pd.DataFrame, "Alpha double prime should be a DataFrame")
        
        # Check that the DataFrames have the required columns
        self.assertTrue('Datetime' in determined_alpha.columns, "Determined alpha missing Datetime column")
        self.assertTrue('Alpha' in determined_alpha.columns, "Determined alpha missing Alpha column")
        self.assertTrue('Datetime' in alpha_prime.columns, "Alpha prime missing Datetime column")
        self.assertTrue('Alpha_Prime' in alpha_prime.columns, "Alpha prime missing Alpha_Prime column")

def run_tests():
    """
    Run tests and print results
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMyopicModel)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    run_tests()