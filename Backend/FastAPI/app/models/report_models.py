from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field
from typing import Annotated, Optional

PyObjectId = Annotated[str, BeforeValidator(str)]


class Report(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_email: EmailStr = Field(...)
    s3_url: str = Field(...)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "user_email": "example@gmail.com",
                "s3_url": "https://s3.amazonaws.com/bucket/key",
            }
        },
    )
