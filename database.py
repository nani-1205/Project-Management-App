# database.py
import pymongo
from pymongo import MongoClient
from bson import ObjectId
import datetime
import traceback # For logging errors
from config import MONGO_URI, DATABASE_NAME

_client = None
_db = None

def connect_db():
    """Establishes connection to the MongoDB database."""
    global _client, _db
    if _client is not None:
        # Check if the connection is still alive, otherwise reset and reconnect
        try:
            _client.admin.command('ping') # Use ping for modern pymongo
            print("MongoDB connection already established and alive.")
            return
        except (pymongo.errors.ConnectionFailure, pymongo.errors.AutoReconnect) as e:
            print(f"MongoDB connection lost ({e}). Attempting to reconnect.")
            _client = None
            _db = None
        except Exception as e: # Catch other potential exceptions during ping
            print(f"Error checking MongoDB connection status ({e}). Attempting to reconnect.")
            _client = None
            _db = None

    # Proceed with connection attempt if _client is None
    try:
        print("Attempting MongoDB connection...")
        _client = MongoClient(MONGO_URI,
                              serverSelectionTimeoutMS=10000, # 10 second timeout
                              connectTimeoutMS=15000, # 15 second connection timeout
                              socketTimeoutMS=15000, # 15 second socket timeout
                              retryWrites=True, # Enable retries for transient network errors
                              retryReads=True)
        # The ismaster command is cheap and does not require auth.
        _client.admin.command('ismaster') # Forces connection check
        _db = _client[DATABASE_NAME]
        print("MongoDB connection successful.")
        # Ensure indexes (safe to call multiple times)
        try:
             _db.projects.create_index("name")
             _db.tasks.create_index("project_id")
             _db.tasks.create_index("status")
             _db.tasks.create_index([("priority", pymongo.ASCENDING)]) # Example specific index
             _db.time_logs.create_index("task_id")
             _db.time_logs.create_index([("log_date", pymongo.DESCENDING)])
             print("Database indexes ensured.")
        except Exception as index_e:
             print(f"Warning: Could not ensure all indexes: {index_e}")

    except (pymongo.errors.ConnectionFailure, pymongo.errors.ServerSelectionTimeoutError) as err:
        print(f"FATAL: MongoDB connection failed: {err}")
        _client = None
        _db = None
        # Re-raise a specific error for the application layer to catch if needed immediately
        raise ConnectionError(f"Could not connect to MongoDB ({MONGO_URI}): {err}")
    except Exception as e:
        print(f"FATAL: An unexpected error occurred during DB connection: {e}")
        traceback.print_exc() # Print full traceback for unexpected errors
        _client = None
        _db = None
        raise ConnectionError(f"Unexpected error connecting to MongoDB: {e}")

def get_db():
    """Returns the database instance, attempting to connect if necessary."""
    if _db is None or _client is None:
        print("Database connection not available in get_db, attempting to establish...")
        try:
            connect_db()
        except ConnectionError as e:
            print(f"Failed to establish connection in get_db: {e}")
            # Re-raise to signal failure to the caller
            raise ConnectionError(f"Database connection failed: {e}")
        # Check again after attempting connection
        if _db is None:
             # This should ideally not happen if connect_db succeeded or raised error
             print("ERROR: connect_db called but _db is still None.")
             raise ConnectionError("Database is not connected after connection attempt.")
    # Optional: Check connection health before returning
    # try:
    #     _client.admin.command('ping')
    # except Exception as e:
    #     print(f"Connection check failed in get_db ({e}), attempting reconnect...")
    #     connect_db() # Try to reconnect
    #     if _db is None: raise ConnectionError("Reconnect failed in get_db")
    return _db

# --- Utility ---
def _get_object_id(id_str):
    """Safely converts a string to ObjectId, raising ValueError on failure."""
    if isinstance(id_str, ObjectId):
        return id_str
    try:
        return ObjectId(id_str)
    except Exception:
        raise ValueError(f"Invalid ID format: '{id_str}' is not a valid ObjectId.")

# --- Project Operations ---
def add_project(name, description="", status="Planning", start_date=None, end_date=None):
    db_conn = get_db()
    project_data = {
        "name": name, "description": description, "status": status,
        "start_date": start_date, "end_date": end_date, # Assume these are already datetime objects
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = db_conn.projects.insert_one(project_data)
    print(f"Added project {result.inserted_id}")
    return result.inserted_id

def get_projects(sort_by="name", sort_order=1):
    db_conn = get_db()
    valid_sort_order = -1 if sort_order == -1 else 1
    return list(db_conn.projects.find().sort(sort_by, valid_sort_order))

def get_project(project_id):
    obj_id = _get_object_id(project_id) # Ensure valid ObjectId
    db_conn = get_db()
    return db_conn.projects.find_one({"_id": obj_id})

def update_project(project_id, updates):
    obj_id = _get_object_id(project_id)
    db_conn = get_db()
    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    # Add validation/type checking for date fields in 'updates' if necessary
    result = db_conn.projects.update_one({"_id": obj_id}, {"$set": updates})
    print(f"Updated project {obj_id}: {'Success' if result.modified_count > 0 else 'No changes'}")
    return result.modified_count > 0

def delete_project(project_id):
    obj_id = _get_object_id(project_id)
    db_conn = get_db()
    tasks_to_delete = list(db_conn.tasks.find({"project_id": obj_id}, {"_id": 1}))
    task_ids = [task["_id"] for task in tasks_to_delete]
    deleted_count = 0
    if task_ids:
        log_del_res = db_conn.time_logs.delete_many({"task_id": {"$in": task_ids}})
        task_del_res = db_conn.tasks.delete_many({"project_id": obj_id})
        print(f"Cascaded delete for project {obj_id}: Deleted {log_del_res.deleted_count} logs, {task_del_res.deleted_count} tasks.")
    proj_del_res = db_conn.projects.delete_one({"_id": obj_id})
    deleted_count = proj_del_res.deleted_count
    print(f"Deleted project {obj_id}: {'Success' if deleted_count > 0 else 'Failed/Not Found'}")
    return deleted_count > 0

# --- Task Operations ---
def add_task(project_id, name, description="", status="To Do", priority="Medium", due_date=None, estimated_hours=None):
    proj_obj_id = _get_object_id(project_id)
    db_conn = get_db()
    task_data = {
        "project_id": proj_obj_id, "name": name, "description": description,
        "status": status, "priority": priority, "due_date": due_date,
        "estimated_hours": estimated_hours, "total_logged_minutes": 0,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = db_conn.tasks.insert_one(task_data)
    print(f"Added task {result.inserted_id} to project {proj_obj_id}")
    return result.inserted_id

def get_tasks_for_project(project_id, sort_by="name", sort_order=1):
    proj_obj_id = _get_object_id(project_id)
    db_conn = get_db()
    valid_sort_order = -1 if sort_order == -1 else 1
    return list(db_conn.tasks.find({"project_id": proj_obj_id}).sort(sort_by, valid_sort_order))

# --- THIS FUNCTION MUST EXIST ---
def get_task(task_id):
    """Fetches a single task by its ID."""
    obj_id = _get_object_id(task_id)
    db_conn = get_db()
    print(f"Fetching task with ID: {obj_id}") # Add log
    task = db_conn.tasks.find_one({"_id": obj_id})
    if task:
        print(f"Found task: {task.get('name')}")
    else:
        print(f"Task with ID {obj_id} not found.")
    return task
# --- END get_task ---

def update_task(task_id, updates):
    obj_id = _get_object_id(task_id)
    db_conn = get_db()
    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    # Add validation for date/numeric types in 'updates' if needed
    result = db_conn.tasks.update_one({"_id": obj_id}, {"$set": updates})
    print(f"Updated task {obj_id}: {'Success' if result.modified_count > 0 else 'No changes'}")
    return result.modified_count > 0

def delete_task(task_id):
    obj_id = _get_object_id(task_id)
    db_conn = get_db()
    # First delete associated time logs
    log_del_res = db_conn.time_logs.delete_many({"task_id": obj_id})
    print(f"Deleted {log_del_res.deleted_count} logs for task {obj_id}")
    # Then delete the task
    task_del_res = db_conn.tasks.delete_one({"_id": obj_id})
    deleted_count = task_del_res.deleted_count
    print(f"Deleted task {obj_id}: {'Success' if deleted_count > 0 else 'Failed/Not Found'}")
    return deleted_count > 0

# --- Time Log Operations ---
def add_time_log(task_id, duration_minutes, log_date=None, notes=""):
    task_obj_id = _get_object_id(task_id)
    db_conn = get_db()

    # Validate and prepare log_date (default to today UTC midnight)
    if log_date is None:
        log_date = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    elif isinstance(log_date, datetime.datetime):
        if log_date.tzinfo is None: # Assume naive dates are UTC
             log_date = log_date.replace(tzinfo=datetime.timezone.utc)
        else: # Convert to UTC if it's aware but different timezone
             log_date = log_date.astimezone(datetime.timezone.utc)
        # Set time to midnight UTC for consistency if only date matters
        log_date = log_date.replace(hour=0, minute=0, second=0, microsecond=0)
    else: # Should not happen if date parsing in app.py is correct
        raise ValueError("Invalid log_date type provided.")

    # Validate duration
    try:
        duration_minutes = int(duration_minutes)
        if duration_minutes <= 0: raise ValueError("Duration must be positive.")
    except (TypeError, ValueError):
        raise ValueError("Duration must be a positive integer number of minutes.")

    # Check if task exists before logging time and incrementing
    task_exists = db_conn.tasks.count_documents({"_id": task_obj_id}) > 0
    if not task_exists:
        raise ValueError(f"Cannot log time: Task with ID {task_obj_id} not found.")

    time_log_data = {
        "task_id": task_obj_id, "log_date": log_date, "duration_minutes": duration_minutes,
        "notes": notes, "created_at": datetime.datetime.now(datetime.timezone.utc)
    }
    # Insert the time log
    log_result = db_conn.time_logs.insert_one(time_log_data)
    print(f"Inserted time log {log_result.inserted_id} for task {task_obj_id}")

    # Increment total logged time on the task
    update_result = db_conn.tasks.update_one(
        {"_id": task_obj_id},
        {"$inc": {"total_logged_minutes": duration_minutes}}
    )
    if update_result.modified_count == 0:
         # This might happen in a race condition, log warning
         print(f"Warning: Failed to increment total_logged_minutes for task {task_obj_id} after adding log {log_result.inserted_id}")

    return log_result.inserted_id

def get_time_logs_for_task(task_id, sort_by="log_date", sort_order=-1):
    obj_id = _get_object_id(task_id)
    db_conn = get_db()
    valid_sort_order = 1 if sort_order == 1 else -1 # Default descending
    return list(db_conn.time_logs.find({"task_id": obj_id}).sort(sort_by, valid_sort_order))