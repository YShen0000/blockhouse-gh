from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field
from typing import Annotated, Optional

PyObjectId = Annotated[str, BeforeValidator(str)]


class Trade(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_email: EmailStr = Field(...)
    institution_id: str = Field(...)
    trades_df: str = Field(...)
    trade_blotter: str = Field(...)
    tickers: str = Field(...)
    data_dict: str = Field(...)
    scaling_factor_report: str = Field(...)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "user_email": "example@gmail.com",
                "trades_df": "{'key': 'value'}",
                "trade_blotter": "{'key': 'value'}",
                "tickers": ["AAPL", "GOOGL"],
                "data_dict": "{'key': 'value'}",
                "scaling_factor_report": "{'key': 'value'}",
            }
        },
    )
