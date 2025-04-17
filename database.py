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
    if _client is None:
        try:
            # Increased timeout slightly, adjust if needed
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
            # The ismaster command is cheap and does not require auth.
            _client.admin.command('ismaster') # Forces connection check
            _db = _client[DATABASE_NAME]
            print("MongoDB connection successful.")
            # Create indexes for faster lookups (run once or ensure they exist)
            # It's okay to call create_index multiple times; MongoDB handles it.
            try:
                 _db.projects.create_index("name")
                 _db.tasks.create_index("project_id")
                 _db.tasks.create_index("status")
                 _db.time_logs.create_index("task_id")
                 print("Database indexes ensured.")
            except Exception as index_e:
                 print(f"Warning: Could not ensure indexes: {index_e}")

        except pymongo.errors.ServerSelectionTimeoutError as err:
            print(f"MongoDB connection failed (Timeout): {err}")
            _client = None
            _db = None
            # Re-raise a specific error for the application layer to catch
            raise ConnectionError(f"Could not connect to MongoDB: Timeout ({MONGO_URI})")
        except pymongo.errors.ConnectionFailure as err:
             print(f"MongoDB connection failed (Connection Failure): {err}")
             _client = None
             _db = None
             raise ConnectionError(f"Could not connect to MongoDB: Connection Failure ({MONGO_URI})")
        except Exception as e:
            print(f"An unexpected error occurred during DB connection: {e}")
            _client = None
            _db = None
            raise ConnectionError(f"Unexpected error connecting to MongoDB: {e}")

def get_db():
    """Returns the database instance, connecting if necessary."""
    # This check ensures that if the initial connect_db failed,
    # subsequent calls won't try to connect again immediately,
    # but will raise an error.
    if _db is None:
        # Optionally, you could attempt to reconnect here, but
        # for simplicity, we rely on the initial connect_db call.
        # connect_db() # Uncomment to try reconnecting on every get_db if connection lost
        if _db is None: # Check again after potentially trying to reconnect
             raise ConnectionError("Database is not connected. Check initial connection logs.")
    return _db

# --- Project Operations ---

def add_project(name, description="", status="Planning", start_date=None, end_date=None):
    db = get_db() # Ensures connection exists
    project_data = {
        "name": name,
        "description": description,
        "status": status,
        "start_date": start_date, # Should be datetime objects if provided
        "end_date": end_date,   # Should be datetime objects if provided
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = db.projects.insert_one(project_data)
    return result.inserted_id

def get_projects(sort_by="name", sort_order=1):
    db = get_db()
    # Ensure sort_order is valid (1 for ascending, -1 for descending)
    valid_sort_order = -1 if sort_order == -1 else 1
    return list(db.projects.find().sort(sort_by, valid_sort_order))

def get_project(project_id):
    # Note: project_id should already be an ObjectId when passed here
    db = get_db()
    if not isinstance(project_id, ObjectId):
        raise ValueError("project_id must be an ObjectId")
    return db.projects.find_one({"_id": project_id})

def update_project(project_id, updates):
    # Note: project_id should already be an ObjectId
    db = get_db()
    if not isinstance(project_id, ObjectId):
        raise ValueError("project_id must be an ObjectId")

    # Ensure dates in updates are datetime objects if present
    for key in ['start_date', 'end_date']:
        if key in updates and updates[key] is not None and not isinstance(updates[key], datetime.datetime):
             # Attempt conversion if string, might need specific format parsing
             try:
                 # Example: Assuming DATE_FORMAT is '%Y-%m-%d'
                 updates[key] = datetime.datetime.strptime(updates[key], '%Y-%m-%d')
             except (TypeError, ValueError):
                 # Handle error or raise if format is unexpected
                 raise ValueError(f"Invalid date format for {key}")


    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    result = db.projects.update_one(
        {"_id": project_id},
        {"$set": updates}
    )
    return result.modified_count > 0

def delete_project(project_id):
    # Note: project_id should already be an ObjectId
    db = get_db()
    if not isinstance(project_id, ObjectId):
        raise ValueError("project_id must be an ObjectId")

    # Cascade delete: Find tasks associated with the project
    tasks_to_delete = list(db.tasks.find({"project_id": project_id}, {"_id": 1}))
    task_ids = [task["_id"] for task in tasks_to_delete]

    # Delete time logs associated with those tasks
    if task_ids:
        db.time_logs.delete_many({"task_id": {"$in": task_ids}})
        print(f"Deleted time logs for {len(task_ids)} tasks in project {project_id}")

        # Delete the tasks themselves
        db.tasks.delete_many({"project_id": project_id})
        print(f"Deleted {len(task_ids)} tasks for project {project_id}")

    # Delete the project itself
    result = db.projects.delete_one({"_id": project_id})
    print(f"Deleted project {project_id}: {'Success' if result.deleted_count > 0 else 'Failed/Not Found'}")
    return result.deleted_count > 0

# --- Task Operations ---

def add_task(project_id, name, description="", status="To Do", priority="Medium", due_date=None, estimated_hours=None):
    # Note: project_id should already be an ObjectId
    db = get_db()
    if not isinstance(project_id, ObjectId):
        raise ValueError("project_id must be an ObjectId")

    task_data = {
        "project_id": project_id,
        "name": name,
        "description": description,
        "status": status,
        "priority": priority,
        "due_date": due_date, # Should be datetime object
        "estimated_hours": estimated_hours, # Should be float or None
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
        "total_logged_minutes": 0 # Initialize logged time
    }
    result = db.tasks.insert_one(task_data)
    return result.inserted_id

def get_tasks_for_project(project_id, sort_by="priority", sort_order=1):
    # Note: project_id should already be an ObjectId
    db = get_db()
    if not isinstance(project_id, ObjectId):
        raise ValueError("project_id must be an ObjectId")
    valid_sort_order = -1 if sort_order == -1 else 1
    # Consider sorting maps if needed (e.g., priority Low->Medium->High)
    # For now, simple alphabetical/numerical sort on the field
    return list(db.tasks.find({"project_id": project_id}).sort(sort_by, valid_sort_order))

def get_task(task_id):
    # Note: task_id should already be an ObjectId
    db = get_db()
    if not isinstance(task_id, ObjectId):
        raise ValueError("task_id must be an ObjectId")
    return db.tasks.find_one({"_id": task_id})

def update_task(task_id, updates):
    # Note: task_id should already be an ObjectId
    db = get_db()
    if not isinstance(task_id, ObjectId):
        raise ValueError("task_id must be an ObjectId")

    # Ensure due_date is datetime if present
    if 'due_date' in updates and updates['due_date'] is not None and not isinstance(updates['due_date'], datetime.datetime):
         try:
              updates['due_date'] = datetime.datetime.strptime(updates['due_date'], '%Y-%m-%d')
         except (TypeError, ValueError):
              raise ValueError("Invalid date format for due_date")

    # Ensure estimated_hours is float or None
    if 'estimated_hours' in updates and updates['estimated_hours'] is not None:
        try:
             updates['estimated_hours'] = float(updates['estimated_hours'])
        except (TypeError, ValueError):
             raise ValueError("Invalid value for estimated_hours")


    updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    result = db.tasks.update_one(
        {"_id": task_id},
        {"$set": updates}
    )
    return result.modified_count > 0

def delete_task(task_id):
    # Note: task_id should already be an ObjectId
    db = get_db()
    if not isinstance(task_id, ObjectId):
        raise ValueError("task_id must be an ObjectId")

    # Delete associated time logs first
    log_delete_result = db.time_logs.delete_many({"task_id": task_id})
    print(f"Deleted {log_delete_result.deleted_count} time logs for task {task_id}")

    # Delete the task
    result = db.tasks.delete_one({"_id": task_id})
    print(f"Deleted task {task_id}: {'Success' if result.deleted_count > 0 else 'Failed/Not Found'}")

    # You might want to update the total logged time on the project if you were tracking it there,
    # but simply deleting the task and its logs is often sufficient.
    return result.deleted_count > 0


# --- Time Log Operations ---

def add_time_log(task_id, duration_minutes, log_date=None, notes=""):
    # Note: task_id should already be an ObjectId
    db = get_db()
    if not isinstance(task_id, ObjectId):
        raise ValueError("task_id must be an ObjectId")

    if log_date is None:
        log_date = datetime.datetime.now(datetime.timezone.utc).date() # Default to today's date
    # Ensure log_date is a datetime object (set time to start of day)
    if isinstance(log_date, datetime.date) and not isinstance(log_date, datetime.datetime):
        log_date = datetime.datetime.combine(log_date, datetime.time.min, tzinfo=datetime.timezone.utc)
    elif isinstance(log_date, datetime.datetime):
        # Ensure it's timezone-aware (UTC)
         if log_date.tzinfo is None:
             # Assuming naive datetime is local, convert carefully or assume UTC
             # For simplicity, let's assume UTC if naive
             log_date = log_date.replace(tzinfo=datetime.timezone.utc)
         else:
             log_date = log_date.astimezone(datetime.timezone.utc)
    else:
         raise ValueError("Invalid log_date provided.")


    # Ensure duration is positive integer
    try:
        duration_minutes = int(duration_minutes)
        if duration_minutes <= 0:
            raise ValueError("Duration must be a positive integer.")
    except (ValueError, TypeError):
        raise ValueError("Invalid duration provided (must be a positive integer).")

    time_log_data = {
        "task_id": task_id,
        "log_date": log_date, # Store as datetime object
        "duration_minutes": duration_minutes,
        "notes": notes,
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }
    result = db.time_logs.insert_one(time_log_data)
    print(f"Added time log {result.inserted_id} for task {task_id}")

    # Update the total logged time on the task using $inc
    update_result = db.tasks.update_one(
        {"_id": task_id},
        {"$inc": {"total_logged_minutes": duration_minutes}}
    )
    if update_result.matched_count == 0:
         # If task wasn't found (maybe deleted just before update?), log a warning.
         # Consider if the time log should be rolled back in a real production scenario.
         print(f"Warning: Task {task_id} not found when trying to update total logged time after adding log {result.inserted_id}.")
    elif update_result.modified_count == 0:
          print(f"Warning: Matched task {task_id} but did not modify total logged time (unexpected).")


    return result.inserted_id

def get_time_logs_for_task(task_id, sort_by="log_date", sort_order=-1):
    # Note: task_id should already be an ObjectId
    db = get_db()
    if not isinstance(task_id, ObjectId):
        raise ValueError("task_id must be an ObjectId")
    valid_sort_order = 1 if sort_order == 1 else -1 # Default descending
    return list(db.time_logs.find({"task_id": task_id}).sort(sort_by, valid_sort_order))

def get_total_logged_time_for_task(task_id):
    """Calculates total time from logs (alternative to relying solely on stored total)"""
    # Note: task_id should already be an ObjectId
    db = get_db()
    if not isinstance(task_id, ObjectId):
        raise ValueError("task_id must be an ObjectId")

    pipeline = [
        {"$match": {"task_id": task_id}},
        {"$group": {"_id": "$task_id", "total_minutes": {"$sum": "$duration_minutes"}}}
    ]
    result = list(db.time_logs.aggregate(pipeline))
    return result[0]['total_minutes'] if result else 0

# --- Utility (Potentially moved to Flask app's utils or kept here) ---
# get_object_id might not be needed if Flask routes handle string-to-ObjectId conversion
# def get_object_id(id_str):
#     """Safely converts a string to ObjectId, handling errors."""
#     try:
#         return ObjectId(id_str)
#     except Exception:
#         return None