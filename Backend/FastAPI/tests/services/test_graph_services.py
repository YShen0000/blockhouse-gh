import pytest
import json
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch
import pandas as pd
import json
from fastapi import HTTPException

from app.services.graph_services import get_trades_data, get_hoodwinked_analyze_plaid, get_hoodwinked_graph_plaid
from app.repositories import graph_repositories
from app.utils import data_fetching_and_preprocessing as dfp

@pytest.mark.asyncio
class TestGetTradesData:
    @pytest.fixture
    def mock_trade_data(self):
        """
        Fixture to create mock trade data for testing
        """
        # Create sample DataFrames
        df = pd.DataFrame({
            'Date': ['2023-01-01', '2023-01-02'],
            'Price': [100.0, 105.0]
        })
        
        trade_blotter = pd.DataFrame({
            'Instrument': ['AAPL', 'GOOGL'],
            'Activity Date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'Quantity': [10, 20]
        })
        
        tickers = ['AAPL', 'GOOGL']
        
        data_dict = {
            'stock_data': pd.DataFrame({
                'Symbol': ['AAPL', 'GOOGL'],
                'Price': [100.0, 200.0]
            })
        }
        
        scaling_factor_report = {
            'AAPL': 1.0,
            'GOOGL': 1.1
        }
        
        return {
            'df': df,
            'trade_blotter': trade_blotter,
            'tickers': tickers,
            'data_dict': data_dict,
            'scaling_factor_report': scaling_factor_report
        }

    @pytest.mark.asyncio
    async def test_get_trades_data_new_data(self, mock_trade_data):
        """
        Test get_trades_data when is_new_data is True or no existing trades
        """
        with patch('app.repositories.graph_repositories.db_get_trades', new_callable=AsyncMock) as mock_db_get_trades, \
             patch('app.repositories.graph_repositories.db_fetch_data_from_s3', new_callable=AsyncMock) as mock_db_fetch_s3, \
             patch('app.repositories.graph_repositories.db_get_trade_blotters') as mock_db_get_trade_blotters, \
             patch('app.repositories.graph_repositories.db_get_scaling_factor') as mock_db_get_scaling_factor, \
             patch('app.repositories.graph_repositories.db_save_trades', new_callable=AsyncMock) as mock_db_save_trades:

            # Mock the dependencies
            mock_db_get_trades.return_value = None
            mock_db_fetch_s3.return_value = mock_trade_data['df']
            mock_db_get_trade_blotters.return_value = (
                mock_trade_data['trade_blotter'], 
                mock_trade_data['tickers'], 
                mock_trade_data['data_dict']
            )
            mock_db_get_scaling_factor.return_value = mock_trade_data['scaling_factor_report']

            # Call the function
            result = await get_trades_data(
                email='test@example.com', 
                platform='test_platform', 
                institution_id='test_institution', 
                is_new_data=True
            )

            # Unpack the result
            df, trade_blotter, tickers, data_dict, scaling_factor_report = result

            # Assertions
            assert not df.empty
            assert not trade_blotter.empty
            assert len(tickers) > 0
            assert isinstance(data_dict, dict)
            assert scaling_factor_report is not None

            # Verify that save_trades was called
            mock_db_save_trades.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_trades_data_existing_trades(self, mock_trade_data):
        """
        Test get_trades_data when existing trades are available
        """
        with patch('app.repositories.graph_repositories.db_get_trades', new_callable=AsyncMock) as mock_db_get_trades:
            # Prepare serialized data to mock existing trades
            serialized_trades = {
                'trades_df': mock_trade_data['df'].to_json(orient='split'),
                'trade_blotter': mock_trade_data['trade_blotter'].to_json(orient='split'),
                'tickers': json.dumps(mock_trade_data['tickers']),
                'data_dict': json.dumps({
                    k: v.to_json(orient='split') if isinstance(v, pd.DataFrame) else v 
                    for k, v in mock_trade_data['data_dict'].items()
                }),
                'scaling_factor_report': json.dumps(mock_trade_data['scaling_factor_report'])
            }

            # Mock the get_trades to return serialized data
            mock_db_get_trades.return_value = serialized_trades

            # Call the function
            result = await get_trades_data(
                email='test@example.com', 
                platform='test_platform', 
                institution_id='test_institution'
            )

            # Unpack the result
            df, trade_blotter, tickers, data_dict, scaling_factor_report = result

            # Assertions
            assert not df.empty
            assert not trade_blotter.empty
            assert len(tickers) > 0
            assert isinstance(data_dict, dict)
            assert scaling_factor_report is not None

            # Verify datetime conversion for trade_blotter
            assert pd.api.types.is_datetime64_any_dtype(trade_blotter['Activity Date'])

    @pytest.mark.asyncio
    async def test_get_trades_data_error_handling(self):
        """
        Test error handling in get_trades_data
        """
        with patch('app.repositories.graph_repositories.db_get_trades', new_callable=AsyncMock) as mock_db_get_trades, \
             patch('app.repositories.graph_repositories.db_fetch_data_from_s3', new_callable=AsyncMock) as mock_db_fetch_s3:

            # Simulate a database fetch error
            mock_db_get_trades.return_value = None
            mock_db_fetch_s3.side_effect = Exception("Database fetch error")

            # Expect an exception to be raised
            with pytest.raises(Exception) as exc_info:
                await get_trades_data(
                    email='test@example.com', 
                    platform='test_platform', 
                    institution_id='test_institution', 
                    is_new_data=True
                )

            assert "Database fetch error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_trades_data_data_transformation(self, mock_trade_data):
        """
        Test data transformation aspects of get_trades_data
        """
        with patch('app.repositories.graph_repositories.db_get_trades', new_callable=AsyncMock) as mock_db_get_trades:
            # Prepare serialized data to mock existing trades
            serialized_trades = {
                'trades_df': mock_trade_data['df'].to_json(orient='split'),
                'trade_blotter': mock_trade_data['trade_blotter'].to_json(orient='split'),
                'tickers': json.dumps(mock_trade_data['tickers']),
                'data_dict': json.dumps({
                    k: v.to_json(orient='split') if isinstance(v, pd.DataFrame) else v 
                    for k, v in mock_trade_data['data_dict'].items()
                }),
                'scaling_factor_report': json.dumps(mock_trade_data['scaling_factor_report'])
            }

            # Mock the get_trades to return serialized data
            mock_db_get_trades.return_value = serialized_trades

            # Call the function
            result = await get_trades_data(
                email='test@example.com', 
                platform='test_platform', 
                institution_id='test_institution'
            )

            # Unpack the result
            df, trade_blotter, tickers, data_dict, scaling_factor_report = result

            # Specific data transformation checks
            assert 'Activity Date' in trade_blotter.columns
            assert all(isinstance(ticker, str) for ticker in tickers)
            assert all(isinstance(v, (pd.DataFrame, dict)) for v in data_dict.values())
            assert isinstance(scaling_factor_report, dict)

@pytest.mark.asyncio
class TestGetHoodwinkedAnalyzePlaid:
    @pytest.fixture
    def mock_trades_data(self):
        """Fixture for mock trades data"""
        df = pd.DataFrame({
            'Date': ['2023-01-01', '2023-01-02'],
            'Price': [100.0, 105.0]
        })
        
        trade_blotter = pd.DataFrame({
            'Instrument': ['AAPL', 'GOOGL'],
            'Activity Date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'Quantity': [10, 20]
        })
        
        tickers = ['AAPL', 'GOOGL']
        
        data_dict = {
            'stock_data': pd.DataFrame({
                'Symbol': ['AAPL', 'GOOGL'],
                'Price': [100.0, 200.0]
            })
        }
        
        scaling_factor_report = {
            'AAPL': 1.0,
            'GOOGL': 1.1
        }
        
        return df, trade_blotter, tickers, data_dict, scaling_factor_report

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_success(self, mock_trades_data):
        """Test successful analysis generation"""
        df, trade_blotter, tickers, data_dict, scaling_factor_report = mock_trades_data
        
        mock_slippage = {"data": "slippage_data"}
        mock_candlestick = {"data": "candlestick_data"}
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value=mock_slippage),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums', return_value=mock_slippage),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_bar_trade_option', return_value=mock_slippage),
            patch('app.utils.data_fetching_and_preprocessing.candle_stick_trade_option', return_value=['option1']),
            patch('app.utils.data_fetching_and_preprocessing.setup_slippage_analysis', return_value=mock_candlestick)
        ):
            result = await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            
            assert "stocks" in result
            assert "slippage_over_time" in result
            assert "slippage_bar_summary" in result
            assert "candle_stick_summary" in result

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_empty_data(self):
        """Test handling of empty data"""
        empty_df = pd.DataFrame()
        empty_trade_blotter = pd.DataFrame()
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=(empty_df, empty_trade_blotter, [], {}, {})),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            
        assert exc_info.value.status_code == 400
        assert "No data returned for trades or DataFrame is empty" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_plotting_error(self, mock_trades_data):
        """Test handling of plotting errors"""
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', side_effect=KeyError("Invalid key")),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            
        assert exc_info.value.status_code == 400
        assert "Invalid data structure for plotting" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_slippage_error(self, mock_trades_data):
        """Test handling of slippage calculation errors"""
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums', side_effect=ValueError("Slippage error")),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            
        assert exc_info.value.status_code == 400
        assert "Failed to calculate slippage values" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_candlestick_error(self, mock_trades_data):
        """Test handling of candlestick chart generation errors"""
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_bar_trade_option', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.candle_stick_trade_option', side_effect=ValueError("Candlestick error")),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
        assert exc_info.value.status_code == 400
        assert str(exc_info.value.detail) == "Candlestick error"

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_trades_data_error(self):
        """Test handling of get_trades_data failure"""
        with (
            patch('app.services.graph_services.get_trades_data', side_effect=Exception("Failed to fetch trades")),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
        assert exc_info.value.status_code == 500
        assert "Failed to fetch trades data" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_nan_handling(self, mock_trades_data):
        """Test handling of NaN values in the data"""
        df, trade_blotter, tickers, data_dict, scaling_factor_report = mock_trades_data
        df.loc[0, 'Price'] = np.nan
        
        mock_response = {
            "value": np.nan,
            "nested": {"value": np.nan},
            "list": [np.nan]
        }
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=(df, trade_blotter, tickers, data_dict, scaling_factor_report)),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value=mock_response),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums', return_value=mock_response),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_bar_trade_option', return_value=mock_response),
            patch('app.utils.data_fetching_and_preprocessing.candle_stick_trade_option', return_value=['option1']),
            patch('app.utils.data_fetching_and_preprocessing.setup_slippage_analysis', return_value=mock_response)
        ):
            result = await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            
            # Check that NaN values were replaced with None
            def check_no_nan(obj):
                if isinstance(obj, dict):
                    return all(check_no_nan(v) for v in obj.values())
                elif isinstance(obj, list):
                    return all(check_no_nan(item) for item in obj)
                return not (isinstance(obj, float) and np.isnan(obj))
            
            assert check_no_nan(result)


    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_date_range(self, mock_trades_data):
        """Test correct date range calculation"""
        df, trade_blotter, tickers, data_dict, scaling_factor_report = mock_trades_data
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_bar_trade_option', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.candle_stick_trade_option', return_value=['option1']),
            patch('app.utils.data_fetching_and_preprocessing.setup_slippage_analysis', return_value={})
        ):
            result = await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            assert "date_range" in result
            assert "start_date" in result["date_range"]
            assert "end_date" in result["date_range"]

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_multiple_candlestick_options(self, mock_trades_data):
        """Test handling of multiple candlestick trade options"""
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_bar_trade_option', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.candle_stick_trade_option', return_value=['option1', 'option2']),
            patch('app.utils.data_fetching_and_preprocessing.setup_slippage_analysis', side_effect=[Exception("First failed"), {}])
        ):
            result = await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            assert "candle_stick_summary" in result

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_line_chart_error(self, mock_trades_data):
        """Test handling of line chart generation errors"""
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', side_effect=KeyError("Line chart error")),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            
        assert exc_info.value.status_code == 400
        assert "Invalid data structure for plotting" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_slippage_bar_calculation_error(self, mock_trades_data):
        """Test handling of slippage bar calculation errors"""
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums', side_effect=ValueError("Slippage calculation error")),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            
        assert exc_info.value.status_code == 400
        assert "Failed to calculate slippage values" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_hoodwinked_analyze_plaid_slippage_bar_trade_option_error(self, mock_trades_data):
        """Test handling of slippage bar trade option calculation errors"""
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums', return_value={}),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_bar_trade_option', side_effect=Exception("Trade option error")),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_analyze_plaid(
                email='test@example.com',
                platform='test_platform',
                institution_id='test_institution'
            )
            
        assert exc_info.value.status_code == 500
        assert "Slippage bar calculation failed" in str(exc_info.value.detail)

@pytest.mark.asyncio
class TestGetHoodwinkedGraphPlaid:
    @pytest.fixture
    def mock_trades_data(self):
        """Fixture for mock trades data"""
        # Create DataFrame with all required columns
        trade_blotter = pd.DataFrame({
            'Instrument': ['AAPL', 'GOOGL'],
            'Activity Date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'Open_Price': [100, 101],
            'Close_Price': [101, 102],
            'TWAP_Price': [100.5, 101.5],
            'VWAP_Price': [100.6, 101.6],
            'HWOE_Price': [100.7, 101.7],
            'Market Volume': [1000, 1100],
            'Volume_Rolling_Mean': [1050, 1050],
            'Volatility': [0.1, 0.11],
            'Volatility_Rolling_Mean': [0.105, 0.105],
            'High': [102, 103],
            'Low': [99, 100],
            'HWOE_Day': [1, 1],
            'HWOE_Time': ['09:30', '10:30'],
            '5d_MA': [100, 101]
        })
        
        df = pd.DataFrame({
            'Date': ['2023-01-01', '2023-01-02'],
            'Price': [100, 105]
        })
        
        return df, trade_blotter, ['AAPL', 'GOOGL'], {'stock_data': df}, {'AAPL': 1.0, 'GOOGL': 1.1}

    @pytest.mark.asyncio
    async def test_get_hoodwinked_graph_plaid_empty_data(self):
        """Test handling of empty data"""
        empty_data = (pd.DataFrame(), pd.DataFrame(), [], {}, {})
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=empty_data),
            pytest.raises(HTTPException) as exc_info
        ):
            await get_hoodwinked_graph_plaid(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="slippage_pie_chart",
                email="test@example.com",
                stock="AAPL",
                benchmark="Close",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
        assert exc_info.value.status_code == 400
        assert "No data returned for trades or DataFrame is empty" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_hoodwinked_graph_plaid_slippage_pie_chart(self, mock_trades_data):
        """Test slippage pie chart generation"""
        mock_pie_data = {"slippage": 0.1, "stock": "AAPL"}
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.slippage_pie_chart', return_value=mock_pie_data),
            patch('app.utils.data_fetching_and_preprocessing.convert_nan_to_null', return_value=mock_pie_data)
        ):
            result = await get_hoodwinked_graph_plaid(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="slippage_pie_chart",
                email="test@example.com",
                stock="AAPL",
                benchmark="Close",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
            assert "slippage_pie_chart" in result

    @pytest.mark.asyncio
    async def test_get_hoodwinked_graph_plaid_slippage_over_time(self, mock_trades_data):
        """Test slippage over time chart generation"""
        mock_time_data = {"time_series": [0.1, 0.2]}
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.plot_excess_returns', return_value=mock_time_data),
            patch('app.utils.data_fetching_and_preprocessing.convert_nan_to_null', return_value=mock_time_data)
        ):
            result = await get_hoodwinked_graph_plaid(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="slippage_over_time",
                email="test@example.com",
                stock="all_trades",
                benchmark="Close",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
            assert "slippage_over_time" in result

    @pytest.mark.asyncio
    async def test_get_hoodwinked_graph_plaid_slippage_bar(self, mock_trades_data):
        """Test slippage bar chart generation"""
        mock_bar_data = {"bar_data": [0.1, 0.2]}
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.calculate_slippage_sums_plaid', return_value=mock_bar_data),
            patch('app.utils.data_fetching_and_preprocessing.convert_nan_to_null', return_value=mock_bar_data)
        ):
            result = await get_hoodwinked_graph_plaid(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="slippage_bar",
                email="test@example.com",
                stock="all_trades",
                benchmark="Close",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
            assert "slippage_bar_data" in result

    @pytest.mark.asyncio
    async def test_get_hoodwinked_graph_plaid_candlestick(self, mock_trades_data):
        """Test candlestick chart generation"""
        mock_candlestick_data = {"candlestick": {"data": [1, 2]}, "stock": "AAPL"}
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.candle_stick_trade_option', return_value=["AAPL_option"]),
            patch('app.utils.data_fetching_and_preprocessing.setup_slippage_analysis', return_value=mock_candlestick_data),
            patch('app.utils.data_fetching_and_preprocessing.convert_nan_to_null', return_value=mock_candlestick_data)
        ):
            result = await get_hoodwinked_graph_plaid(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="candle_stick",
                email="test@example.com",
                stock="AAPL",
                benchmark="Close",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
            assert "candlestick_chart" in result

    @pytest.mark.asyncio
    async def test_get_hoodwinked_graph_plaid_invalid_chart_type(self, mock_trades_data):
        """Test invalid chart type handling"""
        valid_chart_types = ["slippage_pie_chart", "slippage_over_time", "slippage_bar", "candle_stick"]
        
        with (
            patch('app.services.graph_services.get_trades_data', return_value=mock_trades_data),
            patch('app.utils.data_fetching_and_preprocessing.convert_nan_to_null', side_effect=ValueError(f"Invalid chart type. Must be one of {valid_chart_types}"))
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_hoodwinked_graph_plaid(
                    platform="test_platform",
                    institution_id="test_institution",
                    chart_type="invalid_chart",
                    email="test@example.com",
                    stock="AAPL",
                    benchmark="Close",
                    trade_option="All Trades",
                    start_date=None,
                    end_date=None
                )
        
        assert exc_info.value.status_code == 400
        assert "Invalid chart type" in str(exc_info.value.detail)





