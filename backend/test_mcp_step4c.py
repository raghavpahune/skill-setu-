"""Test suite for Task 2 Step 4C: Read-Only Model Context Protocol (MCP) Server."""
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.mcp.server import MCPServer
from app.db import load_demo_data

# Ensure demo baseline is loaded
load_demo_data()
server = MCPServer()


def test_mcp_initialize():
    print("Testing MCP initialize...")
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "test-agent", "version": "1.0"},
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert resp["id"] == 1
    result = resp["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert result["serverInfo"]["name"] == "skillsetu-mcp"
    assert "tools" in result["capabilities"]
    assert "resources" in result["capabilities"]
    print("  OK: MCP initialize passed.")


def test_mcp_tools_list():
    print("Testing MCP tools/list...")
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    resp = server.handle_request(req)
    assert resp is not None
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    expected_tools = ["get_schemes", "get_opportunities", "get_skill_gaps", "get_sync_freshness"]
    for expected in expected_tools:
        assert expected in tool_names, f"Missing tool {expected}"

    for t in tools:
        assert "inputSchema" in t
        assert t["inputSchema"]["type"] == "object"
    print(f"  OK: tools/list returned {len(tools)} tools: {tool_names}")


def test_mcp_tool_calls():
    print("Testing MCP tools/call...")

    # 1. Test get_schemes with category filter
    req_sch = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "get_schemes",
            "arguments": {"category": "SC", "limit": 5},
        },
    }
    resp_sch = server.handle_request(req_sch)
    assert resp_sch is not None
    content_sch = json.loads(resp_sch["result"]["content"][0]["text"])
    assert content_sch["total_returned"] > 0
    for s in content_sch["schemes"]:
        cats = [c.upper() for c in s.get("beneficiary_category", [])]
        assert "SC" in cats or "OPEN" in cats or "ALL" in cats
    print(f"  OK: get_schemes returned {content_sch['total_returned']} schemes.")

    # 2. Test get_opportunities with apprenticeship filter
    req_opp = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "get_opportunities",
            "arguments": {"opportunity_type": "apprenticeship", "limit": 10},
        },
    }
    resp_opp = server.handle_request(req_opp)
    assert resp_opp is not None
    content_opp = json.loads(resp_opp["result"]["content"][0]["text"])
    assert content_opp["total_returned"] >= 3
    for o in content_opp["opportunities"]:
        assert o["opportunity_type"] == "apprenticeship"
        assert "skills" in o
    print(f"  OK: get_opportunities returned {content_opp['total_returned']} apprenticeships.")

    # 3. Test get_skill_gaps
    req_gap = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "get_skill_gaps",
            "arguments": {"limit": 5},
        },
    }
    resp_gap = server.handle_request(req_gap)
    assert resp_gap is not None
    content_gap = json.loads(resp_gap["result"]["content"][0]["text"])
    assert content_gap["total_gaps_calculated"] > 0
    assert len(content_gap["top_gaps"]) <= 5
    first_gap = content_gap["top_gaps"][0]
    assert "skill_name" in first_gap
    assert "gap_pct" in first_gap
    assert "priority" in first_gap
    print(f"  OK: get_skill_gaps returned {len(content_gap['top_gaps'])} top gaps.")

    # 4. Test get_sync_freshness
    req_sync = {
        "jsonrpc": "2.0",
        "id": 13,
        "method": "tools/call",
        "params": {
            "name": "get_sync_freshness",
            "arguments": {},
        },
    }
    resp_sync = server.handle_request(req_sync)
    assert resp_sync is not None
    content_sync = json.loads(resp_sync["result"]["content"][0]["text"])
    assert "status" in content_sync
    assert "total_sync_runs" in content_sync
    assert "active_sources" in content_sync
    # Security check: no secret keys present in content
    raw_text = resp_sync["result"]["content"][0]["text"]
    assert "api_key" not in raw_text.lower() or "configured" in raw_text.lower()
    print("  OK: get_sync_freshness returned clean metadata.")

    # 5. Unknown tool error
    req_unknown = {
        "jsonrpc": "2.0",
        "id": 14,
        "method": "tools/call",
        "params": {
            "name": "delete_all_records",
            "arguments": {},
        },
    }
    resp_unknown = server.handle_request(req_unknown)
    assert resp_unknown is not None
    assert "error" in resp_unknown
    assert resp_unknown["error"]["code"] == -32601
    print("  OK: Unknown tool rejected with code -32601.")


def test_mcp_resources():
    print("Testing MCP resources/list & resources/read...")

    # 1. resources/list
    req_list = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "resources/list",
        "params": {},
    }
    resp_list = server.handle_request(req_list)
    assert resp_list is not None
    resources = resp_list["result"]["resources"]
    uris = [r["uri"] for r in resources]
    assert "skillsetu://schemes/categories" in uris
    assert "skillsetu://opportunities/summary" in uris
    assert "skillsetu://sync/status" in uris
    print(f"  OK: resources/list returned {len(resources)} URIs: {uris}")

    # 2. resources/read for skillsetu://schemes/categories
    req_read1 = {
        "jsonrpc": "2.0",
        "id": 21,
        "method": "resources/read",
        "params": {"uri": "skillsetu://schemes/categories"},
    }
    resp_read1 = server.handle_request(req_read1)
    assert resp_read1 is not None
    content1 = json.loads(resp_read1["result"]["contents"][0]["text"])
    assert "categories" in content1
    assert "scheme_types" in content1
    print(f"  OK: Read skillsetu://schemes/categories.")

    # 3. resources/read for skillsetu://opportunities/summary
    req_read2 = {
        "jsonrpc": "2.0",
        "id": 22,
        "method": "resources/read",
        "params": {"uri": "skillsetu://opportunities/summary"},
    }
    resp_read2 = server.handle_request(req_read2)
    assert resp_read2 is not None
    content2 = json.loads(resp_read2["result"]["contents"][0]["text"])
    assert "total_opportunities" in content2
    assert "by_type" in content2
    print(f"  OK: Read skillsetu://opportunities/summary.")

    # 4. Unknown resource
    req_unknown = {
        "jsonrpc": "2.0",
        "id": 23,
        "method": "resources/read",
        "params": {"uri": "skillsetu://unknown/uri"},
    }
    resp_unknown = server.handle_request(req_unknown)
    assert resp_unknown is not None
    assert "error" in resp_unknown
    assert resp_unknown["error"]["code"] == -32602
    print("  OK: Unknown resource rejected with code -32602.")


if __name__ == "__main__":
    test_mcp_initialize()
    test_mcp_tools_list()
    test_mcp_tool_calls()
    test_mcp_resources()
    print("\nALL MCP STEP 4C TESTS PASSED SUCCESSFULLY!")
