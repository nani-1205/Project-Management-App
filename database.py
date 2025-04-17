# project_tracker/database.py
import pymongo
from pymongo import MongoClient
from bson import ObjectId
import datetime
from config import MONGO_URI, DATABASE_NAME

_client = None
_db = None

def connect_db():
    """Establishes connection to the MongoDB database."""
    global _client, _db
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # 5 second timeout
            # The ismaster command is cheap and does not require auth.
            _client.admin.command('ismaster')
            _db = _client[DATABASE_NAME]
            print("MongoDB connection successful.")
            # Create indexes for faster lookups (optional but recommended)
            _db.projects.create_index("name")
            _db.tasks.create_index("project_id")
            _db.tasks.create_index("status")
            _db.time_logs.create_index("task_id")
        except pymongo.errors.ServerSelectionTimeoutError as err:
            print(f"MongoDB connection failed: {err}")
            _client = None
            _db = None
            raise ConnectionError("Could not connect to MongoDB.")
        except Exception as e:
            print(f"An unexpected error occurred during DB connection: {e}")
            _client = None
            _db = None
            raise

def get_db():
    """Returns the database instance, connecting if necessary."""
    if _db is None:
        connect_db()
    if _db is None:
         # If connect_db failed, raise an error
         raise ConnectionError("Database not connected.")
    return _db

# --- Project Operations ---

def add_project(name, description="", status="Planning", start_date=None, end_date=None):
    db = get_db()
    project_data = {
        "name": name,
        "description": description,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = db.projects.insert_one(project_data)
    return result.inserted_id

def get_projects(sort_by="name", sort_order=1):
    db = get_db()
    return list(db.projects.find().sort(sort_by, sort_order))

def get_project(project_id):
    db = get_db()
    return db.projects.find_one({"_id": ObjectId(project_id)})

def update_project(project_id, updates):
    db = get_db()
    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    result = db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": updates}
    )
    return result.modified_count > 0

def delete_project(project_id):
    db = get_db()
    # Optional: Decide how to handle tasks associated with the deleted project
    # Option 1: Delete associated tasks and time logs (cascade delete)
    tasks_to_delete = list(db.tasks.find({"project_id": ObjectId(project_id)}, {"_id": 1}))
    task_ids = [task["_id"] for task in tasks_to_delete]
    if task_ids:
        db.time_logs.delete_many({"task_id": {"$in": task_ids}})
        db.tasks.delete_many({"project_id": ObjectId(project_id)})

    # Option 2: Keep tasks but maybe mark them as orphaned or prevent project deletion if tasks exist

    # Delete the project itself
    result = db.projects.delete_one({"_id": ObjectId(project_id)})
    return result.deleted_count > 0

# --- Task Operations ---

def add_task(project_id, name, description="", status="To Do", priority="Medium", due_date=None, estimated_hours=None):
    db = get_db()
    task_data = {
        "project_id": ObjectId(project_id),
        "name": name,
        "description": description,
        "status": status,
        "priority": priority,
        "due_date": due_date,
        "estimated_hours": estimated_hours,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
        "total_logged_minutes": 0 # Initialize logged time
    }
    result = db.tasks.insert_one(task_data)
    return result.inserted_id

def get_tasks_for_project(project_id, sort_by="priority", sort_order=1):
    db = get_db()
    # Allow sorting by different fields if needed
    return list(db.tasks.find({"project_id": ObjectId(project_id)}).sort(sort_by, sort_order))

def get_task(task_id):
    db = get_db()
    return db.tasks.find_one({"_id": ObjectId(task_id)})

def update_task(task_id, updates):
    db = get_db()
    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    result = db.tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": updates}
    )
    return result.modified_count > 0

def delete_task(task_id):
    db = get_db()
    # Delete associated time logs first
    db.time_logs.delete_many({"task_id": ObjectId(task_id)})
    # Delete the task
    result = db.tasks.delete_one({"_id": ObjectId(task_id)})
    # After deleting, update the project's total logged time (if we were tracking it there)
    # This might be complex, simpler to recalculate when needed or store on task only
    return result.deleted_count > 0


# --- Time Log Operations ---

def add_time_log(task_id, duration_minutes, log_date=None, notes=""):
    db = get_db()
    if log_date is None:
        log_date = datetime.datetime.now(datetime.timezone.utc) # Store log date

    # Ensure duration is integer
    try:
        duration_minutes = int(duration_minutes)
        if duration_minutes <= 0:
            raise ValueError("Duration must be positive.")
    except (ValueError, TypeError):
        raise ValueError("Invalid duration provided.")

    time_log_data = {
        "task_id": ObjectId(task_id),
        "log_date": log_date,
        "duration_minutes": duration_minutes,
        "notes": notes,
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = db.time_logs.insert_one(time_log_data)

    # Update the total logged time on the task
    update_result = db.tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$inc": {"total_logged_minutes": duration_minutes}}
    )
    if update_result.matched_count == 0:
         # If task wasn't found (maybe deleted?), rollback timelog insert?
         # For simplicity now, we just note it might be inconsistent.
         print(f"Warning: Task {task_id} not found when updating total logged time.")

    return result.inserted_id

def get_time_logs_for_task(task_id, sort_by="log_date", sort_order=-1):
    db = get_db()
    return list(db.time_logs.find({"task_id": ObjectId(task_id)}).sort(sort_by, sort_order))

def get_total_logged_time_for_task(task_id):
    """Calculates total time from logs (alternative to storing on task)"""
    db = get_db()
    pipeline = [
        {"$match": {"task_id": ObjectId(task_id)}},
        {"$group": {"_id": "$task_id", "total_minutes": {"$sum": "$duration_minutes"}}}
    ]
    result = list(db.time_logs.aggregate(pipeline))
    return result[0]['total_minutes'] if result else 0

# --- Utility ---
def get_object_id(id_str):
    """Safely converts a string to ObjectId, handling errors."""
    try:
        return ObjectId(id_str)
    except Exception:
        return None