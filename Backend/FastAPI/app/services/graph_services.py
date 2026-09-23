from io import StringIO
import json
import re
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
import logging


from ..repositories import graph_repositories
from ..utils import data_fetching_and_preprocessing as dfp

logger = logging.getLogger(__name__)


async def get_hoodwinked_analyze_plaid(email: str, platform: str, institution_id: str, is_new_data=False):
    try:
        try:
            df, trade_blotter, tickers, data_dict, scaling_factor_report = await get_trades_data(email, platform, institution_id, is_new_data)
            if df.empty or trade_blotter.empty:
                raise ValueError("No data returned for trades or DataFrame is empty.")
        except ValueError as e:
            logger.error(f"ValueError in get_trades_data: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unhandled exception in get_trades_data: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to fetch trades data.")

        

        # Sanitize the DataFrame by replacing NaN with None
        df = df.replace({np.nan: None})
        trade_blotter_filtered = trade_blotter.copy()
        trade_blotter_filtered = trade_blotter_filtered.replace({np.nan: None})

        # Convert ndarray to list
        instruments_list = tickers

        stock = trade_blotter_filtered["Instrument"].unique().tolist()[0]
        instruments_list = trade_blotter_filtered["Instrument"].unique().tolist()
        benchmark = ["Close", "Open", "TWAP", "VWAP", "HWOE"][0]

        # Line Chart
        try:
            start_date = trade_blotter_filtered["Activity Date"].min()
            end_date = trade_blotter_filtered["Activity Date"].max()
            trade_blotter_filtered_line = trade_blotter.copy()
            instruments_list_line = trade_blotter_filtered_line["Instrument"].tolist()
            slippage_over_time = dfp.plot_excess_returns(
                trade_blotter_filtered_line,
                stock,
                show_open=True,
                show_close=True,
                show_twap=True,
                show_vwap=True,
                show_hwoe=True,
                start_date=start_date,
                end_date=end_date,
                hwoe_adjustment_factor=scaling_factor_report,
                aggregate=True,
            )
        except KeyError as e:
            logger.error(f"KeyError in plot_excess_returns: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid data structure for plotting.")
        except Exception as e:
            logger.error(f"Unhandled exception in plot_excess_returns: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to generate slippage over time.")

        # Slippage Bar
        try:
            slippage_bar = dfp.calculate_slippage_sums(
                trade_blotter, hwoe_adjustment_factor=scaling_factor_report
            )
            slippage_bar_trade_option = dfp.calculate_slippage_bar_trade_option(
                trade_blotter_filtered
            )

        except ValueError as e:
            logger.error(f"ValueError in calculate_slippage: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to calculate slippage values.")
        except Exception as e:
            logger.error(f"Unhandled exception in calculate_slippage: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Slippage bar calculation failed.")
        

        # Candlestick chart
        try:
            candlestick_trade_options = dfp.candle_stick_trade_option(trade_blotter_filtered)
            for i in range(len(candlestick_trade_options)):
                try:
                    candlestick_chart = dfp.setup_slippage_analysis(
                        trade_blotter_filtered, data_dict, candlestick_trade_options[i]
                    )
                    break
                except Exception as e:
                    if i < len(candlestick_trade_options):
                        print(
                            "ERROR: " + str(e) + f". Trying next candlestick_trade_options {i}"
                        )
                    else:
                        raise HTTPException(status_code=400, detail="No valid dates in data")

        except ValueError as e:
            logger.error(f"ValueError in candlestick chart setup: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unhandled exception in candlestick chart setup: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to setup candlestick analysis.")

        def replace_nan_with_none(obj):
            if isinstance(obj, dict):
                return {k: replace_nan_with_none(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_nan_with_none(item) for item in obj]
            elif isinstance(obj, float) and np.isnan(obj):
                return None
            else:
                return obj

        # Replace NaN with None in all data structures
        slippage_over_time = replace_nan_with_none(slippage_over_time)
        slippage_bar = replace_nan_with_none(slippage_bar)
        slippage_bar_trade_option = replace_nan_with_none(slippage_bar_trade_option)
        candlestick_chart = replace_nan_with_none(candlestick_chart)

        response_data = {
            "stocks": instruments_list,
            "stocks_for_line_chart": instruments_list,
            "date_range": {"start_date": start_date, "end_date": end_date},
            "slippage_over_time": slippage_over_time,
            "slippage_bar_summary": {
                "bar_data": slippage_bar,
                "trade_option": slippage_bar_trade_option,
            },
            "candle_stick_summary": {
                "candle_stick_trade_option": candlestick_trade_options,
                "candlestick_chart": candlestick_chart,
            },
        }

        # Replace any remaining NaN values with None in the entire response
        response_data = replace_nan_with_none(response_data)

        return response_data

    except HTTPException as http_exc:
            logger.error(f"HTTPException encountered: {http_exc.detail}")
            raise http_exc

    except Exception as e:
        logger.error(f"Unexpected error in get_hoodwinked_analyze_plaid: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected internal error occurred. Please check logs for details.",
        )


async def get_hoodwinked_graph_plaid(
    platform: str,
    institution_id: str,
    chart_type: str,
    email: str,
    stock: str,
    benchmark: str,
    trade_option: str,
    start_date: str,
    end_date: str,
):
    try:
        try:
            df, trade_blotter, tickers, data_dict, scaling_factor_report = await get_trades_data(email, platform, institution_id)
            if df.empty or trade_blotter.empty:
                raise ValueError("No data returned for trades or DataFrame is empty.")
        except ValueError as e:
            logger.error(f"ValueError in get_trades_data: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unhandled exception in get_trades_data: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to fetch trades data.")

        try:
            trade_blotter_filtered = trade_blotter.copy()
            trade_blotter_filtered = trade_blotter_filtered.dropna(
                how="all",
                subset=[
                    "Open_Price",
                    "Close_Price",
                    "TWAP_Price",
                    "VWAP_Price",
                    "HWOE_Price",
                    "Market Volume",
                    "Volume_Rolling_Mean",
                    "Volatility",
                    "Volatility_Rolling_Mean",
                    "High",
                    "Low",
                    "HWOE_Day",
                    "HWOE_Time",
                    "5d_MA",
                ],
            )

            stock = "all_trades" if stock is None else stock
            if (
                stock not in trade_blotter_filtered["Instrument"].unique().tolist()
                and stock != "all_trades"
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock {stock} not found in the trade blotter, found stocks are {trade_blotter_filtered['Instrument'].unique().tolist()}",
                )
            if start_date is None or (
                pd.to_datetime(start_date, errors="coerce")
                < trade_blotter_filtered["Activity Date"].min()
            ):
                start_date = trade_blotter_filtered["Activity Date"].min()
            if end_date is None or (
                pd.to_datetime(end_date, errors="coerce")
                > trade_blotter_filtered["Activity Date"].max()
            ):
                end_date = trade_blotter_filtered["Activity Date"].max()

        except ValueError as e:
            logger.error(f"ValueError during trade blotter filtering: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unhandled exception during trade blotter filtering: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error filtering trade blotter.")


        try:
            if chart_type == "slippage_pie_chart":
                if benchmark not in ["Close", "Open", "TWAP", "VWAP", "HWOE"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Benchmark {benchmark} is not valid, valid benchmarks are ['Close', 'Open', 'TWAP', 'VWAP', 'HWOE']",
                    )
                # if stock is 'all_trades', return data for all stocks
                if stock == "all_trades":
                    slippage_summary = []
                    for stock in trade_blotter_filtered["Instrument"].unique().tolist():
                        data = dfp.slippage_pie_chart(
                            trade_blotter_filtered, stock, start_date, end_date, benchmark
                        )
                        data["stock"] = stock
                        slippage_summary.append(data)
                # else, return data for the requested stock
                else:
                    slippage_summary = dfp.slippage_pie_chart(
                        trade_blotter_filtered, stock, start_date, end_date, benchmark
                    )
                    slippage_summary["stock"] = stock

                slippage_summary = dfp.convert_nan_to_null(slippage_summary)

                return {"slippage_pie_chart": slippage_summary}

            elif chart_type == "slippage_over_time":
                # Aggregate the data if stock is 'all_trades'
                aggregate = True if stock == "all_trades" else False
                trade_blotter_filtered_line = trade_blotter.copy()

                slippage_over_time = dfp.plot_excess_returns(
                    trade_blotter_filtered_line,
                    stock,
                    show_open=True,
                    show_close=True,
                    show_twap=True,
                    show_vwap=True,
                    show_hwoe=True,
                    start_date=start_date,
                    end_date=end_date,
                    hwoe_adjustment_factor=scaling_factor_report,
                    aggregate=aggregate,
                )
                slippage_over_time = dfp.convert_nan_to_null(slippage_over_time)

                return {"slippage_over_time": slippage_over_time}

            elif chart_type == "slippage_bar":
                slippage_bar = dfp.calculate_slippage_sums_plaid(
                    trade_blotter_filtered,
                    trade_option,
                    hwoe_adjustment_factor=scaling_factor_report,
                )
                slippage_bar = dfp.convert_nan_to_null(slippage_bar)

                return {"slippage_bar_data": slippage_bar}

            elif chart_type == "candle_stick":
                candlestick_trade_options = dfp.candle_stick_trade_option(
                    trade_blotter_filtered
                )
                # If all trades are requested, return data for all stocks using the first trade option found for each stock
                if stock == "all_trades" and trade_option == "All Trades":
                    candlestick_chart = []
                    for stock in trade_blotter_filtered["Instrument"].unique().tolist():
                        valid_stock_idx = next(
                            (
                                i
                                for i, trade_option in enumerate(candlestick_trade_options)
                                if stock in trade_option
                            ),
                            -1,
                        )
                        if valid_stock_idx == -1:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Stock {stock} not found in any trade option, found stocks are {candlestick_trade_options}",
                            )
                        data = dfp.setup_slippage_analysis(
                            trade_blotter_filtered,
                            data_dict,
                            candlestick_trade_options[valid_stock_idx],
                        )
                        data["stock"] = stock
                        candlestick_chart.append(data)
                # else, return data for the requested stock using the first trade option found for that stock
                else:
                    if trade_option != "All Trades":
                        stock = re.search(r"\b[A-Z]+\b", trade_option).group(0)
                    valid_stock_idx = next(
                        (
                            i
                            for i, trade_option in enumerate(candlestick_trade_options)
                            if stock in trade_option
                        ),
                        -1,
                    )
                    if valid_stock_idx == -1:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Stock {stock} not found in any trade option, found stocks are {candlestick_trade_options}",
                        )
                    candlestick_chart = dfp.setup_slippage_analysis(
                        trade_blotter_filtered,
                        data_dict,
                        candlestick_trade_options[valid_stock_idx],
                    )
                    candlestick_chart["stock"] = stock

                candlestick_chart = dfp.convert_nan_to_null(candlestick_chart)

                return {"candlestick_chart": candlestick_chart}
            
            else:
                valid_types = ["slippage_pie_chart", "slippage_over_time", "slippage_bar", "candle_stick"]
                raise ValueError(f"Invalid chart type. Must be one of: {valid_types}")
            
        except ValueError as e:
            logger.error(f"ValueError for chart type processing: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unhandled exception during chart type processing: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Chart processing failed.")
        
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Critical failure in get_hoodwinked_graph_plaid: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


async def get_trades_data(
    email: str, platform: str, institution_id: str, is_new_data=False
):
    trades = await graph_repositories.db_get_trades(email, institution_id)

    if trades is None or is_new_data:
        df = await graph_repositories.db_fetch_data_from_s3(email, institution_id)
        trade_blotter, tickers, data_dict = graph_repositories.db_get_trade_blotters(
            platform, df
        )
        scaling_factor_report = graph_repositories.db_get_scaling_factor(trade_blotter)
        serialized_data_dict = {
            k: v.to_json(orient="split") if isinstance(v, pd.DataFrame) else v
            for k, v in data_dict.items()
        }
        await graph_repositories.db_save_trades(
            email,
            institution_id,
            df,
            trade_blotter,
            tickers,
            serialized_data_dict,
            scaling_factor_report,
        )
    else:
        df = pd.read_json(StringIO(trades["trades_df"]), orient="split")
        trade_blotter = pd.read_json(StringIO(trades["trade_blotter"]), orient="split")
        trade_blotter["Activity Date"] = pd.to_datetime(
            trade_blotter["Activity Date"], unit="ms"
        )
        tickers = json.loads(trades["tickers"])
        serialized_data_dict = json.loads(trades["data_dict"])
        data_dict = {
            k: pd.read_json(StringIO(v), orient="split") if isinstance(v, str) else v
            for k, v in serialized_data_dict.items()
        }
        scaling_factor_report = json.loads(trades["scaling_factor_report"])

    return df, trade_blotter, tickers, data_dict, scaling_factor_report