import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import lancedb
from lancedb.rerankers import AnswerdotaiRerankers
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cps-data")


class CPSSqliteDB:
    def __init__(self, sqlite_path: str):
        self.sqlite_path = str(Path(sqlite_path).expanduser())


    def _execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries"""
        if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
            raise ValueError("Only read queries are allowed!!")

        logger.debug(f"Executing query: {query}")
        try:
            with closing(sqlite3.connect(self.sqlite_path)) as conn:
                conn.row_factory = sqlite3.Row
                with closing(conn.cursor()) as cursor:
                    cursor.execute(query)
                    results = [dict(row) for row in cursor.fetchall()]
                    logger.debug(f"Read query returned {len(results)} rows")
                    return results
        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            raise


class SqliteLanceDB:
    def __init__(self, lancedb_path: str,
                 embedder : str = "nomic-ai/nomic-embed-text-v1.5",
                 reranker : str = "answerdotai/answerai-colbert-small-v1"):
        self.lancedb_path = str(Path(lancedb_path).expanduser())
        self.vector_db = lancedb.connect(self.lancedb_path)
        self.table = self.vector_db.open_table("webpagechunk")
        self.embedder = SentenceTransformer(embedder, trust_remote_code=True)
        self.reranker = AnswerdotaiRerankers(model_type="colbert", model_name=reranker, verbose=0)


    def _execute_query(self, question: str, school_name: str | None = None) -> list[dict[str, Any]]:
        question_embedding = self.embedder.encode(question)
        if not school_name or school_name.strip() == "":
            search = self.table.search(question_embedding).rerank(query_string=question, reranker=self.reranker).limit(10).to_list()
        else:
            search = self.table.search(question_embedding).where(f"metadata.school_name = '{school_name.title()}'", prefilter=True).rerank(query_string=question, reranker=self.reranker).limit(10).to_list()

        return [{"school_name": result["metadata"]["school_name"], "page_url": result["metadata"]["page_url"], "content": result["text"]} for result in search]


async def main(sqlite_path: str, lancedb_path: str):
    from mcp.server.stdio import stdio_server

    logger.info(f"Starting SQLite MCP Server with SQLite DB path: {sqlite_path}")

    sqlitedb = CPSSqliteDB(sqlite_path)
    lancedb = SqliteLanceDB(lancedb_path)

    server = Server("sqlite-manager")

    # Register handlers
    logger.debug("Registering handlers")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        return [
            Tool(
                name="query_schools_and_neighborhoods",
                description="""
                Excecute a SELECT query on a table of Chicago public schools and their neighborhoods called "schooltoneighborhood" with the following schema:
                    id INTEGER NOT NULL, 
                    created_at DATETIME NOT NULL, 
                    school_id INTEGER NOT NULL, 
                    school_name VARCHAR NOT NULL, 
                    neighborhood VARCHAR NOT NULL, 
                    PRIMARY KEY (id)

                "school_name" is always all-caps but "neighborhood" is not.
                """,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SELECT SQL query to execute"},
                    },
                    "required": ["query"],
                }
            ),

            Tool(
                name="query_school_websites",
                description="""
                Query a database of Chicago public school websites for context relevant to answering a given question.
                """,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Question to answer using relevant context from the school websites."},
                        "school_name": {"type": "string", "description": "Optional filter to only search within a specific school's website."}
                    },
                    "required": ["question"],
                }
            )
        ]


    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            if name == "query_schools_and_neighborhoods":
                results = sqlitedb._execute_query(arguments["query"])
                return [TextContent(type="text", text=str(results))]
            elif name == "query_school_websites":
                results = lancedb._execute_query(arguments["question"], arguments.get("school_name", None))
                return [TextContent(type="text", text=str(results))]
            else:
                raise ValueError(f"Unknown tool: {name}")
        except sqlite3.Error as e:
            return [TextContent(type="text", text=f"Database error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]


    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-cps-data",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )