# Cube MCP Server

[![smithery badge](https://smithery.ai/badge/@isaacwasserman/mcp_cube_server)](https://smithery.ai/server/@isaacwasserman/mcp_cube_server)

MCP Server for Interacting with Cube Semantic Layers

## Installation

Install dependencies using uv:

```bash
uv sync
```

## Running the Server

### Command Line

Run the server with required configuration:

```bash
uv run mcp_cube_server --endpoint <cube_endpoint> --api_secret <api_secret>
```

**Note:** You may see a warning about `VIRTUAL_ENV` not matching - this is normal and can be ignored.

### Environment Variables

Alternatively, set environment variables and run without arguments:

```bash
export CUBE_ENDPOINT="https://your-cube-instance.com"
export CUBE_API_SECRET="your-jwt-secret"
export CUBE_TOKEN_PAYLOAD='{"optional": "payload"}'  # Optional
uv run mcp_cube_server
```

### Configuration Options

**Required:**
- `--endpoint` / `CUBE_ENDPOINT`: Cube API endpoint URL
- `--api_secret` / `CUBE_API_SECRET`: JWT signing secret for authentication

**Optional:**
- `CUBE_TOKEN_PAYLOAD`: Additional JWT payload data (JSON string, defaults to `{}`)
- `--log_dir`: Directory for log files
- `--log_level`: Logging level (defaults to INFO)

### Type Checking

Run type checking with:

```bash
uv run pyright
```

## Claude Desktop Setup

To use this MCP server with Claude Desktop, add the following configuration to your `claude_desktop_config.json` file:

### Configuration with Environment Variables (Recommended)

Set your environment variables first:
```bash
export CUBE_ENDPOINT="https://your-cube-instance.com"
export CUBE_API_SECRET="your-jwt-secret"
export CUBE_TOKEN_PAYLOAD='{"optional": "payload"}'  # Optional
```

Then add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "cube": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/cube-mcp-server",
        "run",
        "mcp_cube_server"
      ]
    }
  }
}
```

### Configuration with CLI Arguments

Alternatively, pass configuration directly in the args:
```json
{
  "mcpServers": {
    "cube": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/cube-mcp-server",
        "run",
        "mcp_cube_server",
        "--endpoint",
        "https://your-cube-instance.com",
        "--api_secret",
        "your-jwt-secret"
      ]
    }
  }
}
```

**Note:** Replace `/ABSOLUTE/PATH/TO/cube-mcp-server` with the actual absolute path to this project directory.

The Claude Desktop config file is typically located at:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

## Resources

### `context://data_description`
Contains a description of the data available in the Cube deployment. This is an application controlled version of the `describe_data` tool.

### `data://{data_id}`
Contains the data returned by a `read_data` call in JSON format. This resource is meant for MCP clients that wish to format or otherwise process the output of tool calls. See [`read_data`](#read_data) for more.

## Tools

### `read_data`
Accepts a query to the Cube REST API and returns the data in YAML along with a unique identifier for the data returned. This identifier can be used to a retrieve a JSON representation of the data from the resource `data://{data_id}`. See [`data://{data_id}`](#datadata_id) for more.

### `describe_data`
Describes the data available in the Cube deployment. This is an agentic version of the `context://data_description` resource.

## Usage Examples

### Basic Query
```json
{
  "measures": ["Orders.count"],
  "dimensions": ["Orders.status"],
  "timeDimensions": [{
    "dimension": "Orders.createdAt",
    "granularity": "day",
    "dateRange": "last 7 days"
  }],
  "limit": 100
}
```

### Query with Ordering
```json
{
  "measures": ["Users.count", "Orders.totalAmount"],
  "dimensions": ["Users.city"],
  "order": {"Users.count": "desc"},
  "limit": 10
}
```

### Ungrouped Query (Raw Data)
```json
{
  "dimensions": ["Orders.id", "Orders.status", "Orders.createdAt"],
  "ungrouped": true,
  "limit": 50
}
```
