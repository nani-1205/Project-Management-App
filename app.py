# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from bson import ObjectId, json_util # Import json_util for better serialization
import database as db
from config import APP_TITLE, get_options, DATE_FORMAT
import datetime # <--- IMPORT DATETIME
import json # Import Python's json module

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Needed for flash messages

# --- Database Connection Handling ---
# (Keep your existing connection handling)
try:
    db.connect_db()
except ConnectionError as e:
    print(f"FATAL: Could not connect to MongoDB on startup: {e}")

# --- Utility for JSON serialization ---
def parse_json(data):
    # Use json_util to handle MongoDB specific types like ObjectId and datetime
    return json.loads(json_util.dumps(data))

# --- Context Processor --- ### ADD THIS ###
@app.context_processor
def inject_now():
    """Injects the current UTC datetime into template contexts."""
    return {'now': datetime.datetime.utcnow()}
# --- End Context Processor --- ###

# --- Filters for Jinja2 Templates ---
@app.template_filter('dateformat')
def dateformat(value, format=DATE_FORMAT):
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.strftime(format)
    return value # Return as is if not a datetime object

@app.template_filter('durationformat')
def durationformat(total_minutes):
    if total_minutes is None or total_minutes < 0:
        return "N/A"
    if total_minutes == 0:
        return "0m"
    hours = total_minutes // 60
    minutes = total_minutes % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    return " ".join(parts)


# --- Web Routes ---

@app.route('/')
def index():
    """Main page: Displays projects and potentially tasks for a selected project."""
    try:
        projects = db.get_projects(sort_by="name")
        selected_project_id_str = request.args.get('project_id')
        selected_project = None
        tasks = []
        if selected_project_id_str:
            try:
                selected_project_id = ObjectId(selected_project_id_str) # Convert here
                selected_project = db.get_project(selected_project_id)
                if selected_project:
                    tasks = db.get_tasks_for_project(selected_project_id)
                else:
                     flash(f"Project with ID {selected_project_id_str} not found.", "warning")
                     selected_project_id_str = None # Clear selection if not found
            # Catch specific BSON errors and others
            except (bson.errors.InvalidId, Exception) as e:
                 flash(f"Error loading selected project or tasks: {e}", "error")
                 print(f"ERROR loading project/tasks for ID {selected_project_id_str}: {e}")
                 selected_project_id_str = None # Clear selection on error

        # Now you don't need to explicitly pass 'now' here because the context processor handles it
        return render_template('index.html',
                               title=APP_TITLE,
                               projects=projects,
                               tasks=tasks,
                               selected_project=selected_project,
                               options=get_options())
    except ConnectionError as e:
         flash(f"Database connection error: {e}", "error")
         return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)
    except Exception as e:
        flash(f"An error occurred loading the main page: {e}", "error")
        # Log the error properly in a real app
        print(f"ERROR in index route: {e}") # Keep this for debugging
        # Log the traceback as well for detailed debugging
        import traceback
        traceback.print_exc()
        return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)


# (Keep all other routes: /api/..., /projects/add, /projects/edit, etc.)
# ... rest of your app.py code ...


# --- Run the App ---
if __name__ == '__main__':
    # Use 0.0.0.0 to make it accessible on your network
    # Debug=True is helpful during development (auto-reloads),
    # BUT **NEVER** use debug=True in production!
    app.run(host='0.0.0.0', port=5000, debug=True) # Keep debug=True for now