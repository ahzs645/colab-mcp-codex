# Colab-mcp

An MCP server for bridging your local agent to a Colab session in the browser.

# Supported Clients
This MCP server requires client support for `notifications/tools/list_changed` and for the client to be running locally on your device. 

Popular clients that fit these criteria include:
- Gemini CLI
- Claude Code
- Windsurf

# Codex static proxy

Current Codex Desktop builds may load the initial Colab MCP connection tool
without surfacing notebook tools that appear after `notifications/tools/list_changed`.
This fork adds a static proxy command for those clients:

```toml
[mcp_servers.colab-static-proxy]
command = "uvx"
args = ["git+https://github.com/ahzs645/colab-mcp-codex", "colab-mcp-codex-proxy"]
enabled = true
startup_timeout_sec = 30
tool_timeout_sec = 120
```

Use the proxy tools in this order:

1. `open_colab_browser_connection`
2. `colab_list_tools`
3. `colab_call_tool`

`colab_call_tool` forwards to downstream Colab notebook tools such as
`add_code_cell`, `add_text_cell`, `get_cells`, `update_cell`, `run_code_cell`,
`move_cell`, and `delete_cell`.

# Setup

- Install `uv` (`pip install uv`)
- Configure for usage (eg for mcp.json style services):

```
...
  "mcpServers": {
    "colab-mcp": {
      "command": "uvx",
      "args": ["git+https://github.com/googlecolab/colab-mcp"],
      "timeout": 30000
    }
  }
...
```

(If you have a non-standard default package index (**Googlers**), you may also need to add `--index https://pypi.org/simple`)

# Issues & Discussions

We are using GitHub [discussions](https://github.com/googlecolab/colab-mcp/discussions) as the
place for issue discussion and feature requests. As discussions mature into action items, we
will add those items as issues. This helps us ensure that issues in the issue tracker are
well-understood, deduplicated, and actionable. For these reasons, **please do <u>NOT</u> open
issues directly.** 

# Contributing 
We unfortunately don't have the bandwidth to support review of external contributions, and we 
don't want user PRs to languish, so we aren't accepting any external contributions right now.

If you have a great idea or pain point, we would love to hear about it on our 
[discussions](https://github.com/googlecolab/colab-mcp/discussions) page - the preferred place 
for issue discussion and feature requests.

# Internal - For Colab Developers

### Prerequisites

- `uv` is required (`pip install uv`)
- Configure git hooks to run repo presubmits

```shell
git config core.hooksPath .githooks
```

### Gemini CLI setup

```
...
  "mcpServers": {
    "colab-mcp": {
      "command": "uv",
      "args": ["run", "colab-mcp"],
      "cwd": "/path/to/github/colab-mcp",
      "timeout": 30000
    }
  }
...
```
