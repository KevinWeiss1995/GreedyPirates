import asyncio
import argparse
from pathlib import Path
from src.network.server import GameServer
from src.ui.console import ConsoleUI
from src.utils.config import Config
from src.utils.logger import GameLogger

async def start_server(host: str = None, port: int = None):
    server = GameServer(host=host, port=port)
    await server.start()

async def start_client():
    console = ConsoleUI()
    await console.start()

def main():
    parser = argparse.ArgumentParser(description='Greedy Pirates Game')
    parser.add_argument('--server', action='store_true', help='Run as server')
    parser.add_argument('--host', type=str, help='Server host')
    parser.add_argument('--port', type=int, help='Server port')
    args = parser.parse_args()

    try:
        if args.server:
            print("Starting Greedy Pirates server...")
            asyncio.run(start_server(args.host, args.port))
        else:
            print("Starting Greedy Pirates client...")
            asyncio.run(start_client())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
