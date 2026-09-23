# utils/auth.py

import jwt
from fastapi import Depends, Request, security
from fastapi import HTTPException, status
from ..config.settings import settings


def get_user_email_from_token(request: Request) -> str:
    """
    Extracts the user's email from the JWT token in the Authorization header
    or from the query parameters if the header is missing.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        str: The user's email address.

    Raises:
        HTTPException: If the token is invalid, expired, or email is missing.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        email = request.query_params.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing and email not provided in query params",
            )
        return email

    try:
        token_type, token = auth_header.split(" ")
        if token_type.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    try:
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        email = decoded.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not found in token",
            )
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def docs_authenticate(
    credentials: security.HTTPBasicCredentials = Depends(security.HTTPBasic()),
):
    """
    Authenticates the user for the Swagger UI documentation page.

    Args:
        credentials (security.HTTPBasicCredentials, optional): The username and password. Defaults to Depends(security.HTTPBasic()).

    Raises:
        HTTPException: 401 Unauthorized if the username or password is incorrect.

    Returns:
        security.HTTPBasicCredentials : credentials if the username and password are correct.
    """
    if not (
        credentials.username == settings.DOCS_USERNAME
        and credentials.password == settings.DOCS_PASSWORD
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials
