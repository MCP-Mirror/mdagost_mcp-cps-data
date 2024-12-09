# mcp-cps-data MCP server

A MCP server project for exposing a local SQLite database and a local LanceDB vector database with information on Chicago Public Schools

## Components

### Tools

The server implements two tools:
- query_schools_and_neighborhoods: Excecute a SELECT query on a table of Chicago public schools and their neighborhoods called "schooltoneighborhood" with the following schema:
```
id INTEGER NOT NULL,
created_at DATETIME NOT NULL, 
school_id INTEGER NOT NULL, 
school_name VARCHAR NOT NULL, 
neighborhood VARCHAR NOT NULL, 
PRIMARY KEY (id)
```
  - Takes "query"
- query_school_websites: Query a database of Chicago public school websites for context relevant to answering a given question.

## Configuration
Get the SQlite database and the LanceDB vector database from the [cps-childcare] project(https://github.com/mdagost/cps-childcare).

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "mcp-cps-data": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-cps-data",
        "run",
        "mcp-cps-data",
        "--sqlite-path",
        "/path/to/cps_crawler.db",
        "--lancedb-path",
        "/path/to/embeddings.lancedb"
      ]
    }
  }
  ```
</details>

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-cps-data run mcp-cps-data --sqlite-path /path/to/cps_crawler.db --lancedb-path /path/to/embeddings.lancedb
```


Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.