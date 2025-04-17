# project_tracker/config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Database Configuration ---
# Set your MongoDB Connection String here
# Option 1: Directly in code (less secure, okay for local dev)
# MONGO_URI = "mongodb://localhost:27017/"

# Option 2: From environment variable (Recommended)
# Create a .env file in the project_tracker/ directory with:
# MONGO_URI="your_mongodb_connection_string"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/") # Default if not set
DATABASE_NAME = "project_tracker_db"

# --- UI Configuration ---
APP_TITLE = "Project Pilot"
THEME = "System"  # System, Dark, Light
COLOR_THEME = "blue" # blue, dark-blue, green

# --- Other Settings ---
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

# --- Status/Priority Options ---
TASK_STATUS_OPTIONS = ["To Do", "In Progress", "Blocked", "Review", "Done"]
TASK_PRIORITY_OPTIONS = ["Low", "Medium", "High", "Urgent"]
PROJECT_STATUS_OPTIONS = ["Planning", "Active", "On Hold", "Completed", "Archived"]