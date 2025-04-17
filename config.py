# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Database Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/") # Default if not set
DATABASE_NAME = "project_tracker_db"

# --- UI Configuration (Less relevant for web, but keep for now) ---
APP_TITLE = "Project Pilot (Web)" # Changed title slightly
# THEME = "System"  # Not applicable for web directly
# COLOR_THEME = "blue" # Not applicable for web directly

# --- Other Settings ---
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

# --- Status/Priority Options (Still useful for dropdowns) ---
TASK_STATUS_OPTIONS = ["To Do", "In Progress", "Blocked", "Review", "Done"]
TASK_PRIORITY_OPTIONS = ["Low", "Medium", "High", "Urgent"]
PROJECT_STATUS_OPTIONS = ["Planning", "Active", "On Hold", "Completed", "Archived"]

# Helper function to pass options to templates easily
def get_options():
    return {
        "task_status": TASK_STATUS_OPTIONS,
        "task_priority": TASK_PRIORITY_OPTIONS,
        "project_status": PROJECT_STATUS_OPTIONS,
    }