import os, logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine the project root directory
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SRC_DIR))

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

print(f"Logging directory: {LOG_DIR}")  # Debugging line

# Get log path from environment variable or use default
LOG_FILE = os.getenv("LOG_FILE", os.path.join(LOG_DIR, "error.log"))

def setup_logging():
    # Configure the root logger
    # basicConfig will handle the creation of handlers and their assignment to the root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

# Create the logger instance
# By default, this logger will propagate its messages to the root logger
logger = logging.getLogger("maia")
