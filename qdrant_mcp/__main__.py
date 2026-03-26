"""Entry point for qdrant_mcp server. Supports stdio and streamable-http transports."""

import argparse

from .server import mcp, setup_logging, log


def main():
    parser = argparse.ArgumentParser(description="Qdrant MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP port override (default: 8090)",
    )
    args = parser.parse_args()

    setup_logging(args.transport)

    if args.port is not None:
        mcp.settings.port = args.port

    log.info("Starting with transport=%s", args.transport)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
