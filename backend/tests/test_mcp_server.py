from __future__ import annotations
import pytest
from app.tools.mcp_server import list_mcp_tools, execute_mcp_tool

def test_list_mcp_tools():
    tools = list_mcp_tools()
    assert len(tools) == 8
    tool_names = [t["name"] for t in tools]
    assert "web_search" in tool_names
    assert "verify_domain" in tool_names
    assert "query_factcheck_db" in tool_names
    assert "fetch_article" in tool_names
    assert "pubmed_search" in tool_names
    assert "arxiv_search" in tool_names
    assert "semantic_scholar_search" in tool_names
    assert "image_forensics" in tool_names

def test_execute_mcp_tool_verify_domain():
    resp = execute_mcp_tool("verify_domain", {"domain": "bbc.com"})
    assert resp.is_error is False
    assert len(resp.content) == 1
    assert "bbc.com" in resp.content[0]["text"]

def test_execute_mcp_tool_image_forensics():
    resp = execute_mcp_tool("image_forensics", {"image_path": "test_image.jpg"})
    assert resp.is_error is False
    assert "perceptual_hash" in resp.content[0]["text"]

def test_execute_mcp_tool_unknown():
    resp = execute_mcp_tool("unknown_tool", {})
    assert resp.is_error is True
    assert "Unknown MCP tool capability" in resp.content[0]["text"]
