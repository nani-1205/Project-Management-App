# database.py
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
    if _client is not None: # Already connected or tried connecting
        return
    try:
        print("Attempting MongoDB connection...")
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        _client.admin.command('ismaster') # Check connection
        _db = _client[DATABASE_NAME]
        print("MongoDB connection successful.")
        # Ensure indexes
        try:
             _db.projects.create_index("name")
             _db.tasks.create_index("project_id")
             _db.tasks.create_index("status")
             _db.time_logs.create_index("task_id")
             print("Database indexes ensured.")
        except Exception as index_e:
             print(f"Warning: Could not ensure indexes: {index_e}")
    except (pymongo.errors.ConnectionFailure, pymongo.errors.ServerSelectionTimeoutError) as err:
        print(f"MongoDB connection failed: {err}")
        _client = None
        _db = None
        raise ConnectionError(f"Could not connect to MongoDB ({MONGO_URI})")
    except Exception as e:
        print(f"An unexpected error occurred during DB connection: {e}")
        _client = None
        _db = None
        raise ConnectionError(f"Unexpected error connecting to MongoDB: {e}")

def get_db():
    """Returns the database instance, ensures connection."""
    if _db is None:
        # Try connecting if not already connected (e.g., if initial connect failed but server came up later)
        # This might hide startup errors, so careful logging is important
        print("Database connection was not available, attempting to reconnect...")
        connect_db() # This will raise ConnectionError if it fails again
    return _db

# --- Project Operations ---
def add_project(name, description="", status="Planning", start_date=None, end_date=None):
    db_conn = get_db()
    project_data = {
        "name": name, "description": description, "status": status,
        "start_date": start_date, "end_date": end_date,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = db_conn.projects.insert_one(project_data)
    return result.inserted_id

def get_projects(sort_by="name", sort_order=1):
    db_conn = get_db()
    valid_sort_order = -1 if sort_order == -1 else 1
    return list(db_conn.projects.find().sort(sort_by, valid_sort_order))

def get_project(project_id):
    if not isinstance(project_id, ObjectId): raise ValueError("project_id must be ObjectId")
    db_conn = get_db()
    return db_conn.projects.find_one({"_id": project_id})

def update_project(project_id, updates):
    if not isinstance(project_id, ObjectId): raise ValueError("project_id must be ObjectId")
    db_conn = get_db()
    # Basic date validation/conversion if needed, assuming datetime passed
    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    result = db_conn.projects.update_one({"_id": project_id}, {"$set": updates})
    return result.modified_count > 0

def delete_project(project_id):
    if not isinstance(project_id, ObjectId): raise ValueError("project_id must be ObjectId")
    db_conn = get_db()
    tasks_to_delete = list(db_conn.tasks.find({"project_id": project_id}, {"_id": 1}))
    task_ids = [task["_id"] for task in tasks_to_delete]
    if task_ids:
        db_conn.time_logs.delete_many({"task_id": {"$in": task_ids}})
        db_conn.tasks.delete_many({"project_id": project_id})
    result = db_conn.projects.delete_one({"_id": project_id})
    return result.deleted_count > 0

# --- Task Operations ---
def add_task(project_id, name, description="", status="To Do", priority="Medium", due_date=None, estimated_hours=None):
    if not isinstance(project_id, ObjectId): raise ValueError("project_id must be ObjectId")
    db_conn = get_db()
    task_data = {
        "project_id": project_id, "name": name, "description": description,
        "status": status, "priority": priority, "due_date": due_date,
        "estimated_hours": estimated_hours, "total_logged_minutes": 0,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = db_conn.tasks.insert_one(task_data)
    return result.inserted_id

def get_tasks_for_project(project_id, sort_by="name", sort_order=1): # Default sort by name
    if not isinstance(project_id, ObjectId): raise ValueError("project_id must be ObjectId")
    db_conn = get_db()
    valid_sort_order = -1 if sort_order == -1 else 1
    return list(db_conn.tasks.find({"project_id": project_id}).sort(sort_by, valid_sort_order))

# (Add update_task, delete_task, add_time_log, get_time_logs etc. following similar patterns)