# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
# Import the custom provider and json utils
from flask.json.provider import DefaultJSONProvider

try:
    # Ensure bson imports are correct
    from bson import ObjectId, json_util
    from bson.errors import InvalidId
except ImportError:
    print("ERROR: 'bson' (from pymongo) not found. Please install pymongo: pip install pymongo")
    # Define dummy classes if bson is not found, to avoid early crash before Flask runs
    # This allows Flask to start, but functionality will be broken.
    class ObjectId: pass
    class InvalidId(Exception): pass
    class json_util: # Dummy class if bson fails to import
        @staticmethod
        def dumps(data, **kwargs): import json; return json.dumps(data)
        @staticmethod
        def loads(s, **kwargs): import json; return json.loads(s)

import database as db
from config import APP_TITLE, get_options, DATE_FORMAT
import datetime
import json
import traceback # For detailed error logging

# --- Custom JSON Provider using BSON ---
class BSONJSONProvider(DefaultJSONProvider):
    """
    Custom JSON Provider for Flask that uses bson.json_util
    to handle MongoDB types like ObjectId and datetime correctly.
    """
    def dumps(self, obj, **kwargs):
        # Use bson's json_util.dumps which handles ObjectId and datetime
        return json_util.dumps(obj, **kwargs)

    def loads(self, s, **kwargs):
        # Use bson's json_util.loads
        return json_util.loads(s, **kwargs)
# --- End Custom JSON Provider ---

# --- Flask App Setup ---
app = Flask(__name__)
app.json_provider_class = BSONJSONProvider # Set the custom provider HERE
# Use environment variable for secret key in production, fallback for dev
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
# --- End Flask App Setup ---


# --- Database Connection Handling ---
# Try to connect at startup
try:
    db.connect_db()
    print("Initial Database connection attempt successful.")
except ConnectionError as e:
    print(f"FATAL: Could not connect to MongoDB on startup: {e}")
    # The app might still start, but routes accessing db will likely fail.

# --- Utility for JSON serialization (Potentially less needed now) ---
# def parse_json(data):
#     """Uses json_util to handle MongoDB types like ObjectId and datetime."""
#     # Since we set the app.json_provider_class, jsonify should handle this automatically.
#     # This function might only be needed if you manually dump JSON outside Flask's context.
#     return json.loads(json_util.dumps(data))

# --- Context Processor ---
@app.context_processor
def inject_now():
    """Injects the current UTC datetime into template contexts."""
    return {'now': datetime.datetime.utcnow()}

# --- Filters for Jinja2 Templates ---
@app.template_filter('dateformat')
def dateformat(value, format=DATE_FORMAT):
    """Formats a datetime object into a string for templates."""
    if value is None:
        return ""
    # Handle cases where date might be stored differently (e.g., from BSON/JSON)
    if isinstance(value, dict) and '$date' in value:
         try:
             ts_ms = value['$date']
             # Handle both integer/float milliseconds and ISO string formats
             if isinstance(ts_ms, (int, float)):
                 # Convert milliseconds to seconds for fromtimestamp
                 value = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
             else: # Assuming ISO format string
                 # Ensure timezone info is handled correctly
                 if str(ts_ms).endswith('Z'):
                     ts_ms = str(ts_ms).replace('Z', '+00:00')
                 value = datetime.datetime.fromisoformat(str(ts_ms))
                 # Make sure it's offset-aware (usually UTC from MongoDB)
                 if value.tzinfo is None:
                      value = value.replace(tzinfo=datetime.timezone.utc) # Assume UTC if naive
         except (ValueError, TypeError, KeyError) as e:
             print(f"Error parsing date from BSON dict {value}: {e}")
             return "Invalid Date"
    if isinstance(value, datetime.datetime):
        return value.strftime(format)
    # Attempt to parse if it's a string matching the format
    if isinstance(value, str):
        try:
            dt_obj = datetime.datetime.strptime(value, format)
            return dt_obj.strftime(format) # Reformat to ensure consistency
        except ValueError:
            pass # Ignore if string doesn't match format
    return str(value) # Return as string if not datetime or parsable

@app.template_filter('durationformat')
def durationformat(total_minutes):
    """Formats total minutes into Hh Mm format for templates."""
    if total_minutes is None or not isinstance(total_minutes, (int, float)) or total_minutes < 0:
        return "N/A"
    total_minutes = int(total_minutes) # Ensure integer
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
    """Main page: Displays projects and tasks for a selected project."""
    selected_project_id_str = request.args.get('project_id')
    projects = [] # Default to empty list
    try:
        # Always try to get projects
        projects = db.get_projects(sort_by="name")
    except ConnectionError as e:
         flash(f"Database connection error fetching projects: {e}", "error")
         # Render minimal page if DB fails initially
         # Pass empty lists and no selected project
         return render_template('index.html',
                                title=APP_TITLE, projects=[], tasks=[],
                                selected_project=None, options=get_options(), error=True)
    except Exception as e:
        flash(f"An unexpected error occurred fetching projects: {e}", "error")
        print(f"ERROR in index route (fetching projects): {e}")
        traceback.print_exc()
        return render_template('index.html',
                               title=APP_TITLE, projects=[], tasks=[],
                               selected_project=None, options=get_options(), error=True)

    # Handle selected project and its tasks
    selected_project = None
    tasks = []
    if selected_project_id_str:
        try:
            selected_project_id = ObjectId(selected_project_id_str) # Convert here
            selected_project = db.get_project(selected_project_id)
            if selected_project:
                tasks = db.get_tasks_for_project(selected_project_id)
                # --- Important: Convert dates in selected_project for form pre-population ---
                # The custom JSON provider helps 'tojson', but direct Python access needs handling
                if selected_project.get('start_date') and isinstance(selected_project['start_date'], datetime.datetime):
                     selected_project['start_date_str'] = selected_project['start_date'].strftime('%Y-%m-%d')
                if selected_project.get('end_date') and isinstance(selected_project['end_date'], datetime.datetime):
                     selected_project['end_date_str'] = selected_project['end_date'].strftime('%Y-%m-%d')
                # --- End Date Conversion ---
            else:
                 flash(f"Project with ID {selected_project_id_str} not found.", "warning")
                 selected_project_id_str = None # Clear selection if not found
        except InvalidId:
             flash(f"Invalid Project ID format: {selected_project_id_str}", "error")
             selected_project_id_str = None
        except ConnectionError as e:
             flash(f"Database connection error fetching project/tasks: {e}", "error")
             selected_project_id_str = None # Clear selection on DB error
        except Exception as e:
             flash(f"Error loading selected project or tasks: {e}", "error")
             print(f"ERROR loading project/tasks for ID {selected_project_id_str}: {e}")
             traceback.print_exc()
             selected_project_id_str = None # Clear selection on other errors

    # Render the main template
    # 'now' is injected by the context processor
    return render_template('index.html',
                           title=APP_TITLE,
                           projects=projects,
                           tasks=tasks,
                           selected_project=selected_project,
                           options=get_options())


# --- API Routes (for JavaScript interaction) ---

@app.route('/api/projects/<project_id_str>/tasks')
def get_tasks_api(project_id_str):
    """API endpoint to get tasks for a project."""
    try:
        project_id = ObjectId(project_id_str)
        tasks = db.get_tasks_for_project(project_id)
        # jsonify will now use BSONJSONProvider automatically
        return jsonify(tasks)
    except InvalidId:
        return jsonify({"error": "Invalid Project ID format"}), 400
    except ConnectionError as e:
         return jsonify({"error": f"Database connection error: {e}"}), 500
    except Exception as e:
        print(f"ERROR in get_tasks_api for {project_id_str}: {e}")
        traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

# --- Form Handling Routes ---

# == Projects ==
@app.route('/projects/add', methods=['POST'])
def add_project():
    """Handles adding a new project via form submission."""
    project_name = request.form.get('name', 'Unknown Project') # Get name early for error messages
    try:
        description = request.form.get('description', '')
        status = request.form.get('status', 'Planning')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        # Convert dates, handle empty strings
        start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None

        if not project_name or not project_name.strip():
            flash("Project name is required.", "error")
            return redirect(url_for('index'))

        # Optional: Add validation (e.g., end date >= start date)
        if start_date and end_date and end_date < start_date:
             flash("End date cannot be earlier than start date.", "error")
             # Consider preserving form data on redirect if desired
             return redirect(url_for('index'))

        new_id = db.add_project(name=project_name.strip(), description=description, status=status, start_date=start_date, end_date=end_date)
        flash(f"Project '{project_name.strip()}' added successfully.", "success")
        return redirect(url_for('index', project_id=str(new_id))) # Select the new project
    except ValueError as ve: # Catch specific errors like date format
         flash(f"Input Error adding project '{project_name}': {ve}", "error")
         print(f"VALUE ERROR adding project: {ve}")
    except ConnectionError as e:
         flash(f"Database error adding project '{project_name}': {e}", "error")
         print(f"DB CONNECTION ERROR adding project: {e}")
    except Exception as e:
        flash(f"Error adding project '{project_name}': {e}", "error")
        print(f"ERROR adding project: {e}")
        traceback.print_exc()

    # Redirect to index even if error occurred
    return redirect(url_for('index'))


@app.route('/projects/edit/<project_id_str>', methods=['POST'])
def edit_project(project_id_str):
    """Handles editing an existing project."""
    project_name_new = request.form.get('name', '') # Get new name early
    try:
        project_id = ObjectId(project_id_str)
        updates = {
            "name": project_name_new.strip(),
            "description": request.form.get('description', ''),
            "status": request.form.get('status'),
        }

        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        updates['start_date'] = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        updates['end_date'] = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None

        if not updates["name"]:
            flash("Project name cannot be empty.", "error")
            return redirect(url_for('index', project_id=project_id_str))

        # Optional: Validate date logic
        if updates['start_date'] and updates['end_date'] and updates['end_date'] < updates['start_date']:
             flash("End date cannot be earlier than start date.", "error")
             return redirect(url_for('index', project_id=project_id_str))

        modified = db.update_project(project_id, updates)
        if modified:
            flash(f"Project '{updates['name']}' updated.", "success")
        else:
            flash("No changes detected for the project.", "info")
        return redirect(url_for('index', project_id=project_id_str)) # Keep project selected
    except InvalidId:
        flash(f"Invalid Project ID format for editing: {project_id_str}", "error")
        return redirect(url_for('index'))
    except ValueError as ve:
        flash(f"Input Error updating project '{project_name_new}': {ve}", "error")
        print(f"VALUE ERROR updating project {project_id_str}: {ve}")
        return redirect(url_for('index', project_id=project_id_str))
    except ConnectionError as e:
        flash(f"Database error updating project '{project_name_new}': {e}", "error")
        print(f"DB CONNECTION ERROR updating project {project_id_str}: {e}")
        return redirect(url_for('index', project_id=project_id_str))
    except Exception as e:
        flash(f"Error updating project '{project_name_new}': {e}", "error")
        print(f"ERROR updating project {project_id_str}: {e}")
        traceback.print_exc()
        # Redirect back to the project page on generic error
        return redirect(url_for('index', project_id=project_id_str))


@app.route('/projects/delete/<project_id_str>', methods=['POST']) # Use POST for delete actions
def delete_project(project_id_str):
    """Handles deleting a project."""
    project_name = f"ID {project_id_str}" # Default name
    try:
        project_id = ObjectId(project_id_str)
        # Get name for flash message *before* deleting
        project = db.get_project(project_id)
        if project:
            project_name = project.get('name', project_name)

        deleted = db.delete_project(project_id)
        if deleted:
            flash(f"Project '{project_name}' and its tasks/logs deleted.", "success")
        else:
            flash(f"Project '{project_name}' could not be deleted (maybe it was already removed?).", "warning")
        return redirect(url_for('index')) # Go back to main list
    except InvalidId:
        flash(f"Invalid Project ID format for deletion: {project_id_str}", "error")
    except ConnectionError as e:
        flash(f"Database error deleting project '{project_name}': {e}", "error")
        print(f"DB CONNECTION ERROR deleting project {project_id_str}: {e}")
    except Exception as e:
        flash(f"Error deleting project '{project_name}': {e}", "error")
        print(f"ERROR deleting project {project_id_str}: {e}")
        traceback.print_exc()
    # Redirect to index even if error
    return redirect(url_for('index'))


# == Tasks ==
@app.route('/tasks/add/<project_id_str>', methods=['POST'])
def add_task(project_id_str):
    """Handles adding a new task."""
    task_name = request.form.get('name', 'Unknown Task') # Get name early
    try:
        project_id = ObjectId(project_id_str)
        description = request.form.get('description', '')
        status = request.form.get('status', 'To Do')
        priority = request.form.get('priority', 'Medium')
        due_date_str = request.form.get('due_date')
        due_date = datetime.datetime.strptime(due_date_str, DATE_FORMAT) if due_date_str else None
        est_hours_str = request.form.get('estimated_hours', '').strip()
        estimated_hours = float(est_hours_str) if est_hours_str else None

        if not task_name or not task_name.strip():
            flash("Task name is required.", "error")
            return redirect(url_for('index', project_id=project_id_str))

        # Add validation if needed (e.g., estimated_hours is non-negative)
        if estimated_hours is not None and estimated_hours < 0:
             flash("Estimated hours cannot be negative.", "error")
             return redirect(url_for('index', project_id=project_id_str))

        db.add_task(project_id=project_id, name=task_name.strip(), description=description,
                    status=status, priority=priority, due_date=due_date,
                    estimated_hours=estimated_hours)
        flash(f"Task '{task_name.strip()}' added.", "success")
    except InvalidId:
        flash(f"Invalid Project ID format when adding task: {project_id_str}", "error")
    except ValueError as ve:
         flash(f"Input Error adding task '{task_name}': {ve}", "error")
         print(f"VALUE ERROR adding task to project {project_id_str}: {ve}")
    except ConnectionError as e:
         flash(f"Database error adding task '{task_name}': {e}", "error")
         print(f"DB CONNECTION ERROR adding task to project {project_id_str}: {e}")
    except Exception as e:
        flash(f"Error adding task '{task_name}': {e}", "error")
        print(f"ERROR adding task to project {project_id_str}: {e}")
        traceback.print_exc()

    # Redirect back to the project view regardless of success/failure
    return redirect(url_for('index', project_id=project_id_str))

# == Add routes for editing and deleting tasks similarly... ==
# @app.route('/tasks/edit/<task_id_str>', methods=['POST'])
# def edit_task(task_id_str):
#     # ... implementation needed ...
#     flash("Edit Task functionality not yet implemented.", "info")
#     return redirect(request.referrer or url_for('index'))

# @app.route('/tasks/delete/<task_id_str>', methods=['POST'])
# def delete_task(task_id_str):
#     # ... implementation needed ...
#     flash("Delete Task functionality not yet implemented.", "info")
#     return redirect(request.referrer or url_for('index'))

# == Add routes for adding/viewing time logs... ==
# @app.route('/tasks/<task_id_str>/log_time', methods=['POST'])
# def log_time(task_id_str):
#     # ... implementation needed ...
#    flash("Log Time functionality not yet implemented.", "info")
#    return redirect(request.referrer or url_for('index'))


# --- Run the App ---
if __name__ == '__main__':
    # Set debug=False when running with Gunicorn/uWSGI in production
    # Use environment variable for debug setting, fallback to True for local dev
    debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'

    # Use 0.0.0.0 to make it accessible on your network
    # Port can also be configured via environment variable
    port = int(os.environ.get('PORT', 5000))

    # Turn off reloader if running under PM2 in production
    use_reloader = debug_mode # Simple approach: reloader only if debug is on

    print(f"Starting Flask app: host=0.0.0.0, port={port}, debug={debug_mode}, use_reloader={use_reloader}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=use_reloader)