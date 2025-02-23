import asyncio
import argparse
import logging
from .network.client import GameClient
from .network.server import GameServer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def start_client(host=None, port=None):
    """Start the game client"""
    print("Starting Greedy Pirates client...")
    client = GameClient(host=host, port=port)
    await client.start()

async def start_server():
    """Start the game server"""
    print("Starting Greedy Pirates server...")
    server = GameServer()
    await server.start()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Greedy Pirates Game')
    parser.add_argument('--server', action='store_true', help='Run as server')
    parser.add_argument('--host', type=str, help='Server host address')
    parser.add_argument('--port', type=int, default=8888, help='Server port')
    args = parser.parse_args()
    
    try:
        if args.server:
            asyncio.run(start_server())
        else:
            # Pass host/port to start_client instead of creating client here
            asyncio.run(start_client(host=args.host, port=args.port))
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"\nError: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)

if __name__ == '__main__':
    main() 