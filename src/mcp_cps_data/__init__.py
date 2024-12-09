from . import server
import argparse
import asyncio

def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="CPS Data MCP Server")
    parser.add_argument("--sqlite-path", 
                       help="Path to CPS SQLite database file")
    parser.add_argument("--lancedb-path", 
                       help="Path to LanceDB database file")
    args = parser.parse_args()
    asyncio.run(server.main(args.sqlite_path, args.lancedb_path))

# Optionally expose other important items at package level
__all__ = ['main', 'server']