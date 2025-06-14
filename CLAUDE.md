# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server for interfacing with Cube.dev semantic layers. It provides tools and resources for querying data through Cube's REST API.

## Key Components

- **CubeClient** (`src/mcp_cube_server/server.py:19-101`): Handles JWT authentication, API requests, and response processing for Cube endpoints
- **Query Models** (`src/mcp_cube_server/server.py:103-146`): Pydantic models defining query structure (measures, dimensions, time dimensions, filters)
- **MCP Tools**: `read_data` for querying and `describe_data` for schema information
- **MCP Resources**: `context://data_description` and `data://{data_id}` for data access

## Development Commands

**Install dependencies:**
```bash
uv sync
```

**Run type checking:**
```bash
uv run pyright
```

**Run the server (requires environment variables):**
```bash
mcp_cube_server --endpoint <cube_endpoint> --api_secret <api_secret>
```

## Configuration

The server requires these environment variables or CLI arguments:
- `CUBE_ENDPOINT` / `--endpoint`: Cube API endpoint URL
- `CUBE_API_SECRET` / `--api_secret`: Either a pre-generated API token from Cube Cloud or a JWT signing secret
- `CUBE_TOKEN_PAYLOAD` (optional): Additional JWT payload data (only used in JWT signing mode)

## Architecture Notes

- Uses FastMCP framework for MCP server implementation
- JWT tokens auto-refresh on 403 responses
- Numeric data types are automatically cast from strings
- Query responses include both YAML and JSON formats
- Dynamic resource creation for query results using UUID identifiers
- Request timeout handling with configurable backoff (10s max wait, 1s backoff)