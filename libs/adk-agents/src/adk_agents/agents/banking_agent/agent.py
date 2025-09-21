import os

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

mcp_url = f"http://{os.getenv('ANTHOS_MCP_SERVICE_HOST', 'localhost')}:{os.getenv('ANTHOS_MCP_SERVICE_PORT', 8002)}/mcp"

mcp_connection = StreamableHTTPConnectionParams(url=mcp_url)
mcp_toolset = McpToolset(connection_params=mcp_connection)

root_agent = Agent(
    # A unique name for the agent.
    name="banking_agent",
    # The Large Language Model (LLM) that agent will use.
    model="gemini-2.0-flash-exp",  # if this model does not work, try below
    # model="gemini-2.0-flash-live-001",
    # A short description of the agent's purpose.
    description="Agent to assist with banking inquiries.",
    # Instructions to set the agent's behavior.
    instruction="You are Sam, help the user with the provided banking tools.",
    # Use MCP Server tools.
    tools=[mcp_toolset],
)
