# app.py
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask.json.provider import DefaultJSONProvider

# --- BSON Import Check ---
try:
    from bson import ObjectId, json_util
    from bson.errors import InvalidId
    print("--- Successfully imported ObjectId and json_util from bson ---")
except ImportError:
    print("--- ERROR: Failed to import ObjectId or json_util from bson. ---")
    print("--- Please ensure 'pymongo' is installed correctly. ---")
    sys.exit("Exiting: Required 'bson' components not found.")
# --- End BSON Import Check ---

import database as db
from config import APP_TITLE, get_options, DATE_FORMAT
import datetime
import json
import traceback

# --- Custom JSON Provider (Optional - primarily helps jsonify) ---
class BSONJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        return json_util.dumps(obj, **kwargs)
    def loads(self, s, **kwargs):
        return json_util.loads(s, **kwargs)
# --- End Custom JSON Provider ---

# --- Flask App Setup ---
app = Flask(__name__)
# Uncomment next line if using jsonify extensively and want it to handle BSON
# app.json_provider_class = BSONJSONProvider
# print(f"--- Flask App Created. JSON Provider set to: {app.json_provider_class.__name__} ---")
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
if not app.config['SECRET_KEY'] and not app.debug: # Check if secret key is missing in production
     print("--- WARNING: FLASK_SECRET_KEY not set in environment. Using random key. Flash messages may not persist. ---")
# --- End Flask App Setup ---

# --- Database Connection Handling ---
try:
    db.connect_db()
    print("--- Initial Database connection attempt successful. ---")
except ConnectionError as e:
    # Log fatal error, but allow app to start - routes will handle ConnectionError
    print(f"--- FATAL: Could not connect to MongoDB on startup: {e} ---")

# --- Context Processor ---
@app.context_processor
def inject_now():
    """Injects the current UTC datetime into template contexts."""
    return {'now': datetime.datetime.utcnow()}

# --- Filters for Jinja2 Templates ---
@app.template_filter('dateformat')
def dateformat(value, format=DATE_FORMAT):
    """Formats a datetime object or BSON date dict into a string for templates."""
    if value is None: return ""
    if isinstance(value, dict) and '$date' in value:
         try:
             ts_ms = value['$date']
             if isinstance(ts_ms, (int, float)): value = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
             else:
                 if str(ts_ms).endswith('Z'): ts_ms = str(ts_ms).replace('Z', '+00:00')
                 value = datetime.datetime.fromisoformat(str(ts_ms))
                 if value.tzinfo is None: value = value.replace(tzinfo=datetime.timezone.utc)
         except (ValueError, TypeError, KeyError) as e: print(f"--- WARNING: Error parsing date {value}: {e} ---"); return "Invalid Date"
    if isinstance(value, datetime.datetime): return value.strftime(format)
    if isinstance(value, str): # Attempt to parse string if passed directly
        try: return datetime.datetime.strptime(value, format).strftime(format)
        except ValueError: pass # Ignore if string doesn't match format
    return str(value) # Fallback

@app.template_filter('durationformat')
def durationformat(total_minutes):
    """Formats total minutes into Hh Mm format for templates."""
    if total_minutes is None or not isinstance(total_minutes, (int, float)) or total_minutes < 0: return "N/A"
    total_minutes = int(total_minutes)
    if total_minutes == 0: return "0m"
    hours, minutes = divmod(total_minutes, 60)
    parts = []
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"

@app.template_filter('bson_tojson')
def bson_to_json_filter(value):
    """Custom Jinja2 filter to dump BSON-containing objects to JSON string using json_util."""
    try:
        return json_util.dumps(value)
    except Exception as e:
        print(f"--- ERROR in bson_to_json_filter for value type {type(value)}: {e} ---")
        return "{}" # Return empty JSON object string on error

# --- Web Routes ---
@app.route('/')
def index():
    """Main page: Displays projects and tasks for a selected project."""
    selected_project_id_str = request.args.get('project_id')
    projects, tasks, selected_project = [], [], None
    try:
        projects = db.get_projects(sort_by="name") # Fetch projects first
        if selected_project_id_str:
            try:
                selected_project_id = ObjectId(selected_project_id_str)
                selected_project = db.get_project(selected_project_id)
                if selected_project:
                    tasks = db.get_tasks_for_project(selected_project_id) # Fetch tasks only if project exists
                else:
                    flash(f"Project with ID {selected_project_id_str} not found.", "warning")
            except InvalidId: flash(f"Invalid Project ID format: {selected_project_id_str}", "error")
            except Exception as proj_e:
                print(f"--- ERROR (index): Loading project/tasks {selected_project_id_str}: {proj_e} ---"); traceback.print_exc()
                flash(f"Error loading project details: {proj_e}", "error")
    except ConnectionError as e: print(f"--- ERROR (index): Database connection error: {e} ---"); flash(f"Database connection error: {e}", "error")
    except Exception as e: print(f"--- ERROR (index): Unexpected error: {e} ---"); traceback.print_exc(); flash(f"An unexpected server error occurred: {e}", "error")

    try:
        return render_template('index.html',
                               title=APP_TITLE, projects=projects, tasks=tasks,
                               selected_project=selected_project, options=get_options())
    except Exception as render_e:
        print(f"--- ERROR (index): Exception during render_template: {render_e} ---"); traceback.print_exc()
        return "<h1>Internal Server Error</h1><p>Error rendering page content. Please check server logs.</p>", 500


# --- Form Handling Routes ---

# == Projects ==
@app.route('/projects/add', methods=['POST'])
def add_project():
    project_name = request.form.get('name', '')
    try:
        if not project_name or not project_name.strip(): flash("Project name is required.", "error"); return redirect(url_for('index'))
        start_date_str = request.form.get('start_date'); end_date_str = request.form.get('end_date')
        start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None
        if start_date and end_date and end_date < start_date: flash("End date cannot be earlier than start date.", "error"); return redirect(url_for('index'))
        new_id = db.add_project(name=project_name.strip(), description=request.form.get('description', ''), status=request.form.get('status', 'Planning'), start_date=start_date, end_date=end_date)
        flash(f"Project '{project_name.strip()}' added.", "success"); return redirect(url_for('index', project_id=str(new_id)))
    except (ValueError, ConnectionError) as e: flash(f"Error adding project '{project_name}': {e}", "error")
    except Exception as e: print(f"--- ERROR (add_project): {e} ---"); traceback.print_exc(); flash(f"Unexpected error adding project '{project_name}': {e}", "error")
    return redirect(url_for('index'))

@app.route('/projects/edit/<project_id_str>', methods=['POST'])
def edit_project(project_id_str):
    project_name_new = request.form.get('name', '')
    redirect_url = url_for('index', project_id=project_id_str) # Default redirect back to project
    try:
        project_id = ObjectId(project_id_str)
        if not project_name_new or not project_name_new.strip(): flash("Project name cannot be empty.", "error"); return redirect(redirect_url)
        start_date_str = request.form.get('start_date'); end_date_str = request.form.get('end_date')
        start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None
        if start_date and end_date and end_date < start_date: flash("End date cannot be earlier than start date.", "error"); return redirect(redirect_url)
        updates = { "name": project_name_new.strip(), "description": request.form.get('description', ''), "status": request.form.get('status'), 'start_date': start_date, 'end_date': end_date }
        modified = db.update_project(project_id, updates)
        flash(f"Project '{updates['name']}' updated." if modified else "No changes detected.", "success" if modified else "info")
    except InvalidId: flash(f"Invalid Project ID: {project_id_str}", "error"); redirect_url = url_for('index') # Redirect home if ID invalid
    except (ValueError, ConnectionError) as e: flash(f"Error updating project: {e}", "error")
    except Exception as e: print(f"--- ERROR (edit_project): {e} ---"); traceback.print_exc(); flash(f"Unexpected error updating project: {e}", "error")
    return redirect(redirect_url)

@app.route('/projects/delete/<project_id_str>', methods=['POST'])
def delete_project(project_id_str):
    project_name = f"ID {project_id_str}"
    redirect_url = url_for('index') # Redirect home after delete
    try:
        project_id = ObjectId(project_id_str)
        project = db.get_project(project_id);
        if project: project_name = project.get('name', project_name)
        deleted = db.delete_project(project_id)
        flash(f"Project '{project_name}' deleted." if deleted else f"Project '{project_name}' not found or could not be deleted.", "success" if deleted else "warning")
    except InvalidId: flash(f"Invalid Project ID: {project_id_str}", "error")
    except (ValueError, ConnectionError) as e: flash(f"Error deleting project: {e}", "error")
    except Exception as e: print(f"--- ERROR (delete_project): {e} ---"); traceback.print_exc(); flash(f"Unexpected error deleting project: {e}", "error")
    return redirect(redirect_url)

# == Tasks ==
@app.route('/tasks/add/<project_id_str>', methods=['POST'])
def add_task(project_id_str):
    task_name = request.form.get('name', '')
    redirect_url = url_for('index', project_id=project_id_str) # Default redirect back to project
    try:
        project_id = ObjectId(project_id_str)
        if not task_name or not task_name.strip(): flash("Task name is required.", "error"); return redirect(redirect_url)
        due_date_str = request.form.get('due_date'); est_hours_str = request.form.get('estimated_hours', '').strip()
        due_date = datetime.datetime.strptime(due_date_str, DATE_FORMAT) if due_date_str else None
        estimated_hours = float(est_hours_str) if est_hours_str else None
        if estimated_hours is not None and estimated_hours < 0: flash("Estimated hours cannot be negative.", "error"); return redirect(redirect_url)
        db.add_task( project_id=project_id, name=task_name.strip(), description=request.form.get('description', ''), status=request.form.get('status', 'To Do'), priority=request.form.get('priority', 'Medium'), due_date=due_date, estimated_hours=estimated_hours )
        flash(f"Task '{task_name.strip()}' added.", "success")
    except InvalidId: flash(f"Invalid Project ID: {project_id_str}", "error"); redirect_url = url_for('index') # Go home if project ID invalid
    except (ValueError, ConnectionError) as e: flash(f"Error adding task: {e}", "error")
    except Exception as e: print(f"--- ERROR (add_task): {e} ---"); traceback.print_exc(); flash(f"Unexpected error adding task: {e}", "error")
    return redirect(redirect_url)

@app.route('/tasks/edit/<task_id_str>', methods=['POST'])
def edit_task(task_id_str):
    project_id_to_redirect = request.form.get('project_id_for_redirect')
    task_name = request.form.get('name', 'Unknown Task')
    redirect_url = url_for('index', project_id=project_id_to_redirect) if project_id_to_redirect else url_for('index')
    try:
        task_id = ObjectId(task_id_str)
        updates = { "name": task_name.strip(), "description": request.form.get('description', ''), "status": request.form.get('status'), "priority": request.form.get('priority') }
        due_date_str = request.form.get('due_date'); est_hours_str = request.form.get('estimated_hours', '').strip()
        updates['due_date'] = datetime.datetime.strptime(due_date_str, DATE_FORMAT) if due_date_str else None
        updates['estimated_hours'] = float(est_hours_str) if est_hours_str else None
        if not updates["name"]: flash("Task name cannot be empty.", "error")
        elif updates['estimated_hours'] is not None and updates['estimated_hours'] < 0: flash("Estimated hours cannot be negative.", "error")
        else:
            modified = db.update_task(task_id, updates)
            flash(f"Task '{updates['name']}' updated." if modified else "No changes detected.", "success" if modified else "info")
    except InvalidId: flash(f"Invalid Task ID: {task_id_str}", "error"); redirect_url = url_for('index')
    except ValueError as ve: flash(f"Input Error updating task '{task_name}': {ve}", "error")
    except ConnectionError as e: flash(f"Database error updating task '{task_name}': {e}", "error")
    except Exception as e: print(f"--- ERROR (edit_task): {e} ---"); traceback.print_exc(); flash(f"Unexpected error updating task '{task_name}': {e}", "error")
    return redirect(redirect_url)

@app.route('/tasks/delete/<task_id_str>', methods=['POST'])
def delete_task(task_id_str):
    project_id_to_redirect = request.form.get('project_id_for_redirect')
    task_name = f"ID {task_id_str}"
    redirect_url = url_for('index', project_id=project_id_to_redirect) if project_id_to_redirect else url_for('index')
    try:
        task_id = ObjectId(task_id_str)
        task = db.get_task(task_id);
        if task:
            task_name = task.get('name', task_name)
            if not project_id_to_redirect: # Fallback to get project ID from task
                project_id_to_redirect = str(task.get('project_id'))
                redirect_url = url_for('index', project_id=project_id_to_redirect) if project_id_to_redirect else url_for('index')
        deleted = db.delete_task(task_id)
        flash(f"Task '{task_name}' deleted." if deleted else f"Task '{task_name}' not found or could not be deleted.", "success" if deleted else "warning")
    except InvalidId: flash(f"Invalid Task ID: {task_id_str}", "error"); redirect_url = url_for('index')
    except (ValueError, ConnectionError) as e: flash(f"Error deleting task '{task_name}': {e}", "error")
    except Exception as e: print(f"--- ERROR (delete_task): {e} ---"); traceback.print_exc(); flash(f"Unexpected error deleting task '{task_name}': {e}", "error")
    return redirect(redirect_url)

@app.route('/tasks/log_time/<task_id_str>', methods=['POST'])
def log_time(task_id_str):
    project_id_to_redirect = request.form.get('project_id_for_redirect')
    redirect_url = url_for('index', project_id=project_id_to_redirect) if project_id_to_redirect else url_for('index')
    try:
        task_id = ObjectId(task_id_str)
        duration_str = request.form.get('duration_minutes'); notes = request.form.get('log_notes', ''); log_date_str = request.form.get('log_date')
        if not duration_str: flash("Duration (minutes) is required.", "error")
        else:
            try:
                duration_minutes = int(duration_str)
                if duration_minutes <= 0: flash("Duration must be a positive number of minutes.", "error")
                else:
                    log_date = None; date_error = False
                    if log_date_str:
                        try: log_date = datetime.datetime.strptime(log_date_str, DATE_FORMAT)
                        except ValueError: flash(f"Invalid date format. Please use YYYY-MM-DD.", "error"); date_error = True
                    if not date_error:
                        db.add_time_log(task_id=task_id, duration_minutes=duration_minutes, log_date=log_date, notes=notes)
                        flash(f"{duration_minutes} minute(s) logged successfully.", "success")
            except ValueError: flash("Duration must be a whole number (minutes).", "error")
            except ConnectionError as e: flash(f"Database error logging time: {e}", "error")
            except Exception as e: print(f"--- ERROR (log_time db call): {e} ---"); traceback.print_exc(); flash(f"Error logging time: {e}", "error")
    except InvalidId: flash(f"Invalid Task ID: {task_id_str}", "error"); redirect_url = url_for('index')
    except Exception as e: print(f"--- ERROR (log_time setup): {e} ---"); traceback.print_exc(); flash(f"Unexpected error processing time log: {e}", "error")
    return redirect(redirect_url)


# --- Run the App (Only for direct `python app.py` execution) ---
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'
    port = int(os.environ.get('PORT', 5000))
    use_reloader = False # Keep reloader disabled when using PM2

    print(f"--- Starting Flask app via app.run() [Development Server] ---")
    print(f"--- Config: host=0.0.0.0, port={port}, debug={debug_mode}, use_reloader={use_reloader} ---")
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=use_reloader)