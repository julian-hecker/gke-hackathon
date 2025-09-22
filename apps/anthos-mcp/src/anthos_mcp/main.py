import os
from typing import Annotated
from uuid import uuid4
import jwt
import requests
import time

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import Response


BALANCE_SERVICE_URL = f"http://{os.getenv('BALANCEREADER_SERVICE_HOST', 'localhost')}:{os.getenv('BALANCEREADER_SERVICE_PORT', 8080)}/balances"
USER_SERVICE_URL = f"http://{os.getenv('USERSERVICE_SERVICE_HOST', 'localhost')}:{os.getenv('USERSERVICE_SERVICE_PORT_HTTP', 8081)}/login"
LEDGERWRITER_SERVICE_URL = f"http://{os.getenv('LEDGERWRITER_SERVICE_HOST', 'localhost')}:{os.getenv('LEDGERWRITER_SERVICE_PORT', 8082)}/transactions"

mcp = FastMCP("Anthos MCP")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    return Response(status_code=200)


@mcp.tool()
async def login_for_token(username: str, password: str) -> str:
    """Logs in the user and returns an access token which is used for authenticating to banking services."""
    print(username, password)
    response = requests.get(
        USER_SERVICE_URL, params={"username": username, "password": password}
    )
    if response.status_code != 200:
        return "Login failed"

    token = response.json().get("token")
    return token


@mcp.tool()
def get_balance(access_token: str) -> str:
    """Gets the current balance of the user. Must provide a valid access token from `login_for_token`."""
    try:
        payload = jwt.decode(
            access_token, algorithms=["HS256"], options={"verify_signature": False}
        )
    except jwt.PyJWTError:
        return "Invalid access token"

    exp = payload.get("exp", 0)
    if time.time() > exp:
        return "Access token has expired. Please log in again."

    account_id = payload.get("acct", "")
    if not account_id:
        return "Invalid access token"

    response = requests.get(
        f"{BALANCE_SERVICE_URL}/{account_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != 200:
        return "Failed to get balance"

    balance = response.json() or 0
    return f"Your balance is ${balance / 100:.2f} USD"


@mcp.tool()
def add_transaction(
    access_token: Annotated[str, "Access token from login"],
    to_account: Annotated[str, "Account number to send money to"],
    amount: Annotated[float, "Amount to send, in US Dollars"],
) -> str:
    """Adds a transaction to the ledger. Must provide a valid access token from `login_for_token`."""
    try:
        payload = jwt.decode(
            access_token, algorithms=["HS256"], options={"verify_signature": False}
        )
    except jwt.PyJWTError:
        return "Invalid access token"

    exp = payload.get("exp", 0)
    if time.time() > exp:
        return "Access token has expired. Please log in again."

    account_id = payload.get("acct", "")
    if not account_id:
        return "Invalid access token"

    transaction = {
        "fromAccountNum": account_id,
        "toAccountNum": to_account,
        "amount": amount / 100,  # convert dollars to cents
        "toRoutingNum": "883745000",  # Hardcoded fake routing number
        "fromRoutingNum": "883745000",  # Hardcoded fake routing number
        "uuid": uuid4().hex,
    }

    response = requests.post(
        LEDGERWRITER_SERVICE_URL,
        json=transaction,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if not response.ok:
        return "Failed to add transaction: " + response.text

    return "Transaction added successfully"


app = mcp.http_app()
