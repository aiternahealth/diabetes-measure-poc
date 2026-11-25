"""Print the Claude Desktop config entry for the DCG MCP server (paths resolved for this machine)."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
entry = {"mcpServers": {"dcg-care-gaps": {
    "command": str(root / ".venv" / "bin" / "python"),
    "args": [str(root / "agent" / "mcp_server.py")],
    "env": {"DCG_DUCKDB": str(root / "data" / "dcg.duckdb")},
}}}
print("Add this to ~/Library/Application Support/Claude/claude_desktop_config.json (merge into an existing \"mcpServers\"),")
print("then quit and reopen Claude Desktop:\n")
print(json.dumps(entry, indent=2))
