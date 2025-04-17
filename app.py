# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
# Ensure bson is imported correctly
try:
    from bson import ObjectId, json_util
    from bson.errors import InvalidId
except ImportError:
    print("Make sure 'bson' (from pymongo) is installed.")
    # Define dummy classes if bson is not found, to avoid early crash before Flask runs
    class ObjectId: pass
    class InvalidId(Exception): pass
    class json_util:
        @staticmethod
        def dumps(data): import json; return json.dumps(data)

import database as db
from config import APP_TITLE, get_options, DATE_FORMAT
import datetime
import json
import traceback # For detailed error logging

# --- Flask App Setup ---
app = Flask(__name__)
# Use environment variable for secret key in production, fallback for dev
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Database Connection Handling ---
# Try to connect at startup
try:
    db.connect_db()
    print("Initial Database connection attempt successful.")
except ConnectionError as e:
    print(f"FATAL: Could not connect to MongoDB on startup: {e}")
    # The app might still start, but routes accessing db will fail.

# --- Utility for JSON serialization ---
def parse_json(data):
    """Uses json_util to handle MongoDB types like ObjectId and datetime."""
    return json.loads(json_util.dumps(data))

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
    # Handle cases where date might be stored differently (e.g., from BSON)
    if isinstance(value, dict) and '$date' in value:
         # Handle BSON date format often seen after json_util.dumps
         try:
             # Value['$date'] might be milliseconds (int/float) or ISO string
             ts_ms = value['$date']
             if isinstance(ts_ms, (int, float)):
                 value = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
             else: # Assuming ISO format string
                 value = datetime.datetime.fromisoformat(str(ts_ms).replace('Z', '+00:00'))
         except (ValueError, TypeError, KeyError):
             return "Invalid Date" # Or handle error differently
    if isinstance(value, datetime.datetime):
        return value.strftime(format)
    return str(value) # Return as string if not datetime

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
    try:
        # Always try to get projects
        projects = db.get_projects(sort_by="name")
    except ConnectionError as e:
         flash(f"Database connection error fetching projects: {e}", "error")
         # Render minimal page if DB fails initially
         return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)
    except Exception as e:
        flash(f"An unexpected error occurred fetching projects: {e}", "error")
        print(f"ERROR in index route (fetching projects): {e}")
        traceback.print_exc()
        return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)

    # Handle selected project and its tasks
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
        # Use parse_json which uses json_util for proper BSON serialization
        return jsonify(parse_json(tasks))
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
    project_name = "" # Initialize for flash message on error
    try:
        name = request.form.get('name')
        project_name = name # Store for potential flash message
        description = request.form.get('description', '')
        status = request.form.get('status', 'Planning')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        # Convert dates, handle empty strings
        start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None

        if not name:
            flash("Project name is required.", "error")
            return redirect(url_for('index'))

        # Optional: Add validation (e.g., end date >= start date)
        if start_date and end_date and end_date < start_date:
             flash("End date cannot be earlier than start date.", "error")
             # Consider preserving form data on redirect if desired
             return redirect(url_for('index'))

        new_id = db.add_project(name=name, description=description, status=status, start_date=start_date, end_date=end_date)
        flash(f"Project '{name}' added successfully.", "success")
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
    project_name = "" # Initialize
    try:
        project_id = ObjectId(project_id_str)
        updates = {
            "name": request.form.get('name'),
            "description": request.form.get('description', ''),
            "status": request.form.get('status'),
        }
        project_name = updates["name"] # Store for flash message

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
        flash(f"Input Error updating project '{project_name}': {ve}", "error")
        print(f"VALUE ERROR updating project {project_id_str}: {ve}")
        return redirect(url_for('index', project_id=project_id_str))
    except ConnectionError as e:
        flash(f"Database error updating project '{project_name}': {e}", "error")
        print(f"DB CONNECTION ERROR updating project {project_id_str}: {e}")
        return redirect(url_for('index', project_id=project_id_str))
    except Exception as e:
        flash(f"Error updating project '{project_name}': {e}", "error")
        print(f"ERROR updating project {project_id_str}: {e}")
        traceback.print_exc()
        # Redirect to main page if update fails badly
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
    # Redirect to index even if error, maybe keep selection if delete failed?
    # Pass project_id back if you want to keep it selected on failure:
    # return redirect(url_for('index', project_id=project_id_str))
    return redirect(url_for('index'))


# == Tasks ==
@app.route('/tasks/add/<project_id_str>', methods=['POST'])
def add_task(project_id_str):
    """Handles adding a new task."""
    task_name = "" # Initialize
    try:
        project_id = ObjectId(project_id_str)
        name = request.form.get('name')
        task_name = name # Store for flash
        description = request.form.get('description', '')
        status = request.form.get('status', 'To Do')
        priority = request.form.get('priority', 'Medium')
        due_date_str = request.form.get('due_date')
        due_date = datetime.datetime.strptime(due_date_str, DATE_FORMAT) if due_date_str else None
        est_hours_str = request.form.get('estimated_hours', '').strip()
        estimated_hours = float(est_hours_str) if est_hours_str else None

        if not name:
            flash("Task name is required.", "error")
            return redirect(url_for('index', project_id=project_id_str))

        # Add validation if needed (e.g., estimated_hours is non-negative)
        if estimated_hours is not None and estimated_hours < 0:
             flash("Estimated hours cannot be negative.", "error")
             return redirect(url_for('index', project_id=project_id_str))

        db.add_task(project_id=project_id, name=name, description=description,
                    status=status, priority=priority, due_date=due_date,
                    estimated_hours=estimated_hours)
        flash(f"Task '{name}' added.", "success")
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
#     # 1. Get task_id = ObjectId(task_id_str)
#     # 2. Get form data (name, description, status, priority, due_date, estimated_hours)
#     # 3. Validate data (name required, dates, hours format)
#     # 4. Call db.update_task(task_id, updates_dict)
#     # 5. Flash success/info/error message
#     # 6. Redirect back to the project view (need project_id from task or query param)
#     #    task = db.get_task(task_id)
#     #    project_id = task['project_id'] if task else None
#     #    return redirect(url_for('index', project_id=str(project_id)))
#     flash("Edit Task functionality not yet implemented.", "info")
#     # Find which project this task belongs to redirect back
#     # This requires fetching the task or having project_id passed somehow
#     return redirect(request.referrer or url_for('index')) # Go back or to index

# @app.route('/tasks/delete/<task_id_str>', methods=['POST'])
# def delete_task(task_id_str):
#     # 1. Get task_id = ObjectId(task_id_str)
#     # 2. Optional: Get task name for flash message before deleting
#     #    task = db.get_task(task_id)
#     #    task_name = task['name'] if task else 'the task'
#     #    project_id = task['project_id'] if task else None
#     # 3. Call db.delete_task(task_id)
#     # 4. Flash success/error message
#     # 5. Redirect back to the project view
#     #    return redirect(url_for('index', project_id=str(project_id)))
#     flash("Delete Task functionality not yet implemented.", "info")
#     return redirect(request.referrer or url_for('index'))

# == Add routes for adding/viewing time logs... ==
# @app.route('/tasks/<task_id_str>/log_time', methods=['POST'])
# def log_time(task_id_str):
#     # 1. Get task_id = ObjectId(task_id_str)
#     # 2. Get form data (duration_minutes, log_date, notes)
#     # 3. Validate data (duration > 0, date format)
#     # 4. Call db.add_time_log(...)
#     # 5. Flash success/error
#     # 6. Redirect back to project view
#     #    task = db.get_task(task_id)
#     #    project_id = task['project_id'] if task else None
#     #    return redirect(url_for('index', project_id=str(project_id)))
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

    app.run(host='0.0.0.0', port=port, debug=debug_mode)