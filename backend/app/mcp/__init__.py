"""SkillSetu MCP (Model Context Protocol) Server package.

Provides read-only access to welfare schemes, opportunities, labour-market
skill gaps, and ingestion freshness for AI agents via standard JSON-RPC 2.0.
"""
from app.mcp.server import MCPServer
from app.mcp.tools import TOOLS
from app.mcp.resources import RESOURCES

__all__ = ["MCPServer", "TOOLS", "RESOURCES"]
