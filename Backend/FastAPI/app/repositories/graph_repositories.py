from io import StringIO
from bson import ObjectId
from fastapi import HTTPException
import pandas as pd
import json
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from ..config.s3 import s3
from ..config.database import db
from ..utils import data_fetching_and_preprocessing as dfp
from ..utils import report_calculation as rc
from ..models.trades_models import Trade


async def db_get_trades(user_email: str, institution_id: str) -> dict:
    # Fetch the trade document by user_email
    trade_doc = await db.get_collection("Trades").find_one(
        {"user_email": user_email, "institution_id": institution_id}
    )
    if not trade_doc:
        return None  # Return None if no trades are found

    # Initialize GridFS bucket
    fs_bucket = AsyncIOMotorGridFSBucket(db)

    # Retrieve `data_dict` from GridFS if it exists
    if "data_dict" in trade_doc:
        try:
            # The `data_dict` field contains the GridFS file ID
            data_dict_id = ObjectId(trade_doc["data_dict"])
            grid_out = await fs_bucket.open_download_stream(data_dict_id)
            data_dict_json = (await grid_out.read()).decode("utf-8")
            trade_doc["data_dict"] = data_dict_json
        except Exception as e:
            print(f"Error retrieving data_dict: {str(e)}")
            trade_doc["data_dict"] = None  # Handle missing or corrupted GridFS data
            trade_doc["error"] = f"Error retrieving data_dict: {str(e)}"

    # Return the updated trade document
    return trade_doc


async def db_save_trades(
    user_email: str,
    institution_id: str,
    trades: pd.DataFrame,
    trade_blotter: pd.DataFrame,
    tickers: list,
    data_dict: dict,
    scaling_factor_report: dict,
):
    # Convert data to JSON strings
    trades_json = trades.to_json(orient="split")
    trade_blotter_json = trade_blotter.to_json(orient="split")
    tickers_json = json.dumps(tickers)
    scaling_factor_report_json = json.dumps(scaling_factor_report)

    # Initialize GridFS bucket
    fs_bucket = AsyncIOMotorGridFSBucket(db)

    # Save large `data_dict` in GridFS
    data_dict_json = json.dumps(data_dict)
    data_dict_id = await fs_bucket.upload_from_stream(
        f"data_dict_{user_email}", data_dict_json.encode("utf-8")
    )

    # Save the trade document in the database
    trade = Trade(
        user_email=user_email,
        institution_id=institution_id,
        trades_df=trades_json,
        trade_blotter=trade_blotter_json,
        tickers=tickers_json,
        data_dict=str(data_dict_id),
        scaling_factor_report=scaling_factor_report_json,
    )

    await db.get_collection("Trades").update_one(
        {"user_email": user_email, "institution_id": institution_id},
        {"$set": trade.model_dump(by_alias=True, exclude=["id"])},
        upsert=True,
    )


async def db_fetch_data_from_s3(email: str, institution_id: str) -> pd.DataFrame:
    # Fetch data from S3
    filepath = f"hoodwinked/plaid/{email}/{institution_id}.csv"
    file_content = s3.download(filepath)

    # Read the CSV file into a DataFrame
    df = pd.read_csv(StringIO(file_content.decode("utf-8")))

    return df


def db_get_trade_blotters(platform: str, df: pd.DataFrame):
    # Preprocess data if not in cache
    trade_blotter = dfp.preprocess_by_platform(df, platform)
    tickers = (
        trade_blotter["Instrument"].unique().tolist()
    )  # Convert to list for JSON serialization
    trade_blotter, data_dict = dfp.preprocess_data_merged(trade_blotter)

    return trade_blotter, tickers, data_dict


def db_get_scaling_factor(trade_blotter: pd.DataFrame):
    reports = rc.calculate_potential_savings(trade_blotter)["scaling_factor"]
    return reports