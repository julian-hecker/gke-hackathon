import jwt
import requests

from fastmcp import Context, FastMCP


BALANCE_SERVICE_URL = "http://localhost:8080/balances/"
USER_SERVICE_URL = "http://localhost:8081/login"

mcp = FastMCP("Anthos MCP")


@mcp.tool()
async def login(username: str, password: str, ctx: Context) -> str:
    """Logs in the user"""
    response = requests.get(USER_SERVICE_URL, params={"username": username, "password": password})
    if response.status_code != 200:
        return "Login failed"
    
    token = response.json().get("token")
    print(token)
    payload = jwt.decode(token, algorithms=["HS256"], options={"verify_signature": False})
    print(payload)
    exp = payload.get("exp", 0)
    account_id = payload.get("acct", "")

    ctx.set_state("username", username)
    ctx.set_state("account_id", account_id)
    ctx.set_state("expires_at", exp)

    print(ctx._state)

    return "Logged in"


@mcp.tool()
def get_balance(ctx: Context) -> str:
    """Gets the current balance of the user. Must be logged in first."""
    print(ctx._state)
    if not ctx.get_state("account_id"):
        return "User not logged in. Please use the `login` tool first."
    return "10000"


app = mcp.http_app()

if __name__ == "__main__":
    mcp.run()
