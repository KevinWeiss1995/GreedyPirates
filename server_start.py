import asyncio
import argparse
import logging
from src.network.server import GameServer

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

async def main(host: str, port: int, min_players: int):
    setup_logging()
    logger = logging.getLogger(__name__)
    
    server = GameServer(host=host, port=port)
    
    logger.info(f"Starting Greedy Pirates server on {host}:{port}")
    logger.info(f"Waiting for {min_players} players to join...")
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        server.stop()
        logger.info("Server stopped")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Greedy Pirates game server")
    parser.add_argument('--host', default='localhost', help='Host address to bind to')
    parser.add_argument('--port', type=int, default=8888, help='Port to listen on')
    parser.add_argument('--min-players', type=int, default=3, help='Minimum number of players needed to start')
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.host, args.port, args.min_players))
    except KeyboardInterrupt:
        print("\nServer startup cancelled") 