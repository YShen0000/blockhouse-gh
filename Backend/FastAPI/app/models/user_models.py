from pydantic import BaseModel, field_validator
from typing import List, Dict, Any


class UserTransactions(BaseModel):
    """
    Pydantic model representing user transactions.

    Attributes:
        json_data (List[Dict[str, Any]]): List of transaction data.
        user_email (str): User's email address.
    """

    json_data: List[Dict[str, Any]]
    user_email: str
    institution_id: str

    @field_validator("json_data")
    def check_json_data_not_empty(cls, v):
        if not v or all(not item for item in v):
            raise ValueError("json_data cannot be empty or contain empty dictionaries")
        return v
