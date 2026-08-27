"""SkillSetu MCP (Model Context Protocol) Server.

Implements a compliant JSON-RPC 2.0 MCP server over stdio for external AI agents
(e.g., Claude Desktop, Antigravity, Cursor, or autonomous CLI agents) to safely
read student welfare schemes, opportunities, labour-market skill gaps, and sync status.
"""
import json
import logging
import sys
from typing import Any

from app.db import load_demo_data
from app.mcp.tools import TOOLS
from app.mcp.resources import RESOURCES

logger = logging.getLogger("skillsetu.mcp")


class MCPServer:
    """Standard JSON-RPC 2.0 Model Context Protocol Server."""

    PROTOCOL_VERSION = "2024-11-05"
    SERVER_NAME = "skillsetu-mcp"
    SERVER_VERSION = "0.1.0"

    def __init__(self):
        # Ensure demo data is loaded if running in demo mode
        load_demo_data()

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Handle an incoming JSON-RPC 2.0 request or notification."""
        method = request.get("method")
        msg_id = request.get("id")
        params = request.get("params", {})

        # Notifications (no id) require no response
        if msg_id is None and method in ("notifications/initialized", "initialized"):
            logger.info("MCP Client initialized.")
            return None

        # Standard methods
        if method == "initialize":
            return self._make_response(msg_id, {
                "protocolVersion": self.PROTOCOL_VERSION,
                "serverInfo": {
                    "name": self.SERVER_NAME,
                    "version": self.SERVER_VERSION,
                },
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
            })

        elif method == "ping":
            return self._make_response(msg_id, {})

        elif method == "tools/list":
            tools_list = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"],
                }
                for tool in TOOLS.values()
            ]
            return self._make_response(msg_id, {"tools": tools_list})

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name not in TOOLS:
                return self._make_error_response(msg_id, -32601, f"Unknown tool: {tool_name}")

            try:
                result = TOOLS[tool_name]["handler"](tool_args)
                return self._make_response(msg_id, {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2),
                        }
                    ]
                })
            except Exception as exc:
                logger.exception("Error executing tool %s: %s", tool_name, exc)
                return self._make_response(msg_id, {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing {tool_name}: {str(exc)}",
                        }
                    ]
                })

        elif method == "resources/list":
            resources_list = [
                {
                    "uri": res["uri"],
                    "name": res["name"],
                    "description": res["description"],
                    "mimeType": res["mimeType"],
                }
                for res in RESOURCES.values()
            ]
            return self._make_response(msg_id, {"resources": resources_list})

        elif method == "resources/read":
            uri = params.get("uri")
            if uri not in RESOURCES:
                return self._make_error_response(msg_id, -32602, f"Resource not found: {uri}")

            try:
                result = RESOURCES[uri]["handler"]()
                return self._make_response(msg_id, {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": RESOURCES[uri]["mimeType"],
                            "text": json.dumps(result, indent=2),
                        }
                    ]
                })
            except Exception as exc:
                logger.exception("Error reading resource %s: %s", uri, exc)
                return self._make_error_response(msg_id, -32603, f"Error reading {uri}: {str(exc)}")

        else:
            return self._make_error_response(msg_id, -32601, f"Method not found: {method}")

    def run_stdio(self):
        """Run standard I/O loop reading JSON-RPC messages from stdin and writing to stdout."""
        logger.info("Starting %s MCP Server on stdio...", self.SERVER_NAME)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as exc:
                logger.exception("Malformed MCP message: %s", exc)

    @staticmethod
    def _make_response(msg_id: Any, result: Any) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }

    @staticmethod
    def _make_error_response(msg_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message,
            },
        }


if __name__ == "__main__":
    server = MCPServer()
    server.run_stdio()
