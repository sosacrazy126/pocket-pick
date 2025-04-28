import logging
from pathlib import Path
from src.mcp_server_pocket_pick.modules.functionality.index_patterns import get_index

# Configure logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    patterns_dir = Path("patterns/")
    index_file = Path("data/pattern_index.json")

    logger.info(f"Starting index build for patterns in: {patterns_dir.resolve()}")
    logger.info(f"Index will be saved to: {index_file.resolve()}")

    try:
        # Ensure data directory exists
        index_file.parent.mkdir(exist_ok=True)
        
        # Build the index, forcing a rebuild
        index = get_index(base_path=str(patterns_dir), index_path=index_file, force_rebuild=True)
        
        if index:
            logger.info(f"Successfully built and saved index with {len(index)} patterns.")
        else:
            logger.warning("Index building completed, but the index is empty. Check patterns directory and permissions.")
            
    except Exception as e:
        logger.error(f"An error occurred during index building: {e}", exc_info=True) 