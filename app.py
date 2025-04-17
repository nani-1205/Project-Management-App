# app.py
import os
import sys # Import sys for exit on critical error
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
# Import the custom provider and json utils
from flask.json.provider import DefaultJSONProvider

# --- Critical BSON Import Check ---
try:
    from bson import ObjectId, json_util
    from bson.errors import InvalidId
    print("--- Successfully imported ObjectId and json_util from bson ---")
    # Test if json_util can actually dump an ObjectId
    try:
        test_oid = ObjectId()
        print(f"--- json_util test dump: {json_util.dumps({'test': test_oid})} ---")
    except Exception as e:
        print(f"--- ERROR: json_util failed test dump: {e} ---")
        sys.exit("Exiting: bson.json_util seems broken.")

except ImportError:
    print("--- ERROR: Failed to import ObjectId or json_util from bson. ---")
    print("--- Please ensure 'pymongo' is installed correctly in the virtual environment. ---")
    print("--- Application cannot function correctly. Exiting. ---")
    sys.exit("Exiting: Required 'bson' components not found.")
# --- End BSON Import Check ---


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
        # Add a debug print to see if this method is called
        # print(f"--- DEBUG: BSONJSONProvider.dumps called for obj of type {type(obj)} ---")
        try:
            result = json_util.dumps(obj, **kwargs)
            return result
        except Exception as e:
            print(f"--- ERROR in BSONJSONProvider.dumps: {e} ---")
            raise

    def loads(self, s, **kwargs):
        # Use bson's json_util.loads
        # print(f"--- DEBUG: BSONJSONProvider.loads called ---")
        return json_util.loads(s, **kwargs)
# --- End Custom JSON Provider ---

# --- Flask App Setup ---
app = Flask(__name__)
# Set the custom provider HERE
app.json_provider_class = BSONJSONProvider
print(f"--- Flask App Created. JSON Provider set to: {app.json_provider_class.__name__} ---")
# Use environment variable for secret key in production, fallback for dev
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
# --- End Flask App Setup ---


# --- Database Connection Handling ---
try:
    db.connect_db()
    print("--- Initial Database connection attempt successful. ---")
except ConnectionError as e:
    print(f"--- FATAL: Could not connect to MongoDB on startup: {e} ---")

# --- Context Processor ---
@app.context_processor
def inject_now():
    """Injects the current UTC datetime into template contexts."""
    return {'now': datetime.datetime.utcnow()}

# --- Filters for Jinja2 Templates ---
@app.template_filter('dateformat')
def dateformat(value, format=DATE_FORMAT):
    """Formats a datetime object into a string for templates."""
    if value is None: return ""
    if isinstance(value, dict) and '$date' in value:
         try:
             ts_ms = value['$date']
             if isinstance(ts_ms, (int, float)): value = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
             else:
                 if str(ts_ms).endswith('Z'): ts_ms = str(ts_ms).replace('Z', '+00:00')
                 value = datetime.datetime.fromisoformat(str(ts_ms))
                 if value.tzinfo is None: value = value.replace(tzinfo=datetime.timezone.utc)
         except (ValueError, TypeError, KeyError) as e:
             print(f"--- WARNING: Error parsing date from BSON dict {value}: {e} ---")
             return "Invalid Date"
    if isinstance(value, datetime.datetime): return value.strftime(format)
    if isinstance(value, str):
        try: return datetime.datetime.strptime(value, format).strftime(format)
        except ValueError: pass
    return str(value)

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


# --- Web Routes ---
@app.route('/')
def index():
    """Main page: Displays projects and tasks for a selected project."""
    # print("--- Entering index route ---") # Keep debug prints if needed
    selected_project_id_str = request.args.get('project_id')
    projects = []
    try:
        # print("--- Fetching projects from DB ---")
        projects = db.get_projects(sort_by="name")
        # print(f"--- Found {len(projects)} projects ---")
    except ConnectionError as e:
         print(f"--- ERROR (index): Database connection error fetching projects: {e} ---")
         flash(f"Database connection error fetching projects: {e}", "error")
         return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)
    except Exception as e:
        print(f"--- ERROR (index): Unexpected error fetching projects: {e} ---")
        traceback.print_exc()
        flash(f"An unexpected error occurred fetching projects: {e}", "error")
        return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)

    selected_project = None
    tasks = []
    if selected_project_id_str:
        # print(f"--- Handling selected project ID: {selected_project_id_str} ---")
        try:
            selected_project_id = ObjectId(selected_project_id_str)
            # print(f"--- Fetching project {selected_project_id} from DB ---")
            selected_project = db.get_project(selected_project_id)
            if selected_project:
                # print(f"--- Found selected project: {selected_project.get('name')} ---")
                # print(f"--- Fetching tasks for project {selected_project_id} from DB ---")
                tasks = db.get_tasks_for_project(selected_project_id)
                # print(f"--- Found {len(tasks)} tasks ---")
            else:
                 # print(f"--- WARNING (index): Project with ID {selected_project_id_str} not found in DB. ---")
                 flash(f"Project with ID {selected_project_id_str} not found.", "warning")
                 selected_project_id_str = None
        except InvalidId:
             # print(f"--- ERROR (index): Invalid Project ID format: {selected_project_id_str} ---")
             flash(f"Invalid Project ID format: {selected_project_id_str}", "error")
             selected_project_id_str = None
        except ConnectionError as e:
             # print(f"--- ERROR (index): Database connection error fetching project/tasks: {e} ---")
             flash(f"Database connection error fetching project/tasks: {e}", "error")
             selected_project_id_str = None
        except Exception as e:
             # print(f"--- ERROR (index): Error loading selected project or tasks: {e} ---")
             traceback.print_exc()
             flash(f"Error loading selected project or tasks: {e}", "error")
             selected_project_id_str = None

    # print("--- Rendering index.html template ---")
    try:
        # Pass necessary variables to the template
        return render_template('index.html',
                               title=APP_TITLE,
                               projects=projects,
                               tasks=tasks,
                               selected_project=selected_project,
                               options=get_options())
    except Exception as render_e:
        print(f"--- ERROR (index): Exception during render_template: {render_e} ---")
        traceback.print_exc()
        flash(f"Error rendering page: {render_e}", "error")
        return "<h1>Internal Server Error</h1><p>Error rendering template. Check logs.</p>", 500


# --- API Routes ---
@app.route('/api/projects/<project_id_str>/tasks')
def get_tasks_api(project_id_str):
    """API endpoint to get tasks for a project."""
    # ... (keep implementation) ...
    try:
        project_id = ObjectId(project_id_str)
        tasks = db.get_tasks_for_project(project_id)
        return jsonify(tasks)
    except InvalidId: return jsonify({"error": "Invalid Project ID format"}), 400
    except ConnectionError as e: return jsonify({"error": f"Database connection error: {e}"}), 500
    except Exception as e:
        print(f"--- ERROR (get_tasks_api): {e} ---"); traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

# --- Form Handling Routes ---
# == Projects ==
@app.route('/projects/add', methods=['POST'])
def add_project():
    # ... (keep implementation) ...
    project_name = request.form.get('name', 'Unknown Project')
    try:
        description = request.form.get('description', '')
        status = request.form.get('status', 'Planning')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None
        if not project_name or not project_name.strip():
            flash("Project name is required.", "error"); return redirect(url_for('index'))
        if start_date and end_date and end_date < start_date:
             flash("End date cannot be earlier than start date.", "error"); return redirect(url_for('index'))
        new_id = db.add_project(name=project_name.strip(), description=description, status=status, start_date=start_date, end_date=end_date)
        flash(f"Project '{project_name.strip()}' added successfully.", "success")
        return redirect(url_for('index', project_id=str(new_id)))
    except ValueError as ve: flash(f"Input Error adding project '{project_name}': {ve}", "error")
    except ConnectionError as e: flash(f"Database error adding project '{project_name}': {e}", "error")
    except Exception as e: print(f"--- ERROR (add_project): {e} ---"); traceback.print_exc(); flash(f"Error adding project '{project_name}': {e}", "error")
    return redirect(url_for('index'))

@app.route('/projects/edit/<project_id_str>', methods=['POST'])
def edit_project(project_id_str):
    # ... (keep implementation) ...
    project_name_new = request.form.get('name', '')
    try:
        project_id = ObjectId(project_id_str)
        updates = { "name": project_name_new.strip(), "description": request.form.get('description', ''), "status": request.form.get('status'), }
        start_date_str = request.form.get('start_date'); end_date_str = request.form.get('end_date')
        updates['start_date'] = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        updates['end_date'] = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None
        if not updates["name"]: flash("Project name cannot be empty.", "error"); return redirect(url_for('index', project_id=project_id_str))
        if updates['start_date'] and updates['end_date'] and updates['end_date'] < updates['start_date']:
             flash("End date cannot be earlier than start date.", "error"); return redirect(url_for('index', project_id=project_id_str))
        modified = db.update_project(project_id, updates)
        if modified: flash(f"Project '{updates['name']}' updated.", "success")
        else: flash("No changes detected for the project.", "info")
        return redirect(url_for('index', project_id=project_id_str))
    except InvalidId: flash(f"Invalid Project ID format for editing: {project_id_str}", "error"); return redirect(url_for('index'))
    except ValueError as ve: flash(f"Input Error updating project '{project_name_new}': {ve}", "error"); return redirect(url_for('index', project_id=project_id_str))
    except ConnectionError as e: flash(f"Database error updating project '{project_name_new}': {e}", "error"); return redirect(url_for('index', project_id=project_id_str))
    except Exception as e: print(f"--- ERROR (edit_project): {e} ---"); traceback.print_exc(); flash(f"Error updating project '{project_name_new}': {e}", "error"); return redirect(url_for('index', project_id=project_id_str))

@app.route('/projects/delete/<project_id_str>', methods=['POST'])
def delete_project(project_id_str):
    # ... (keep implementation) ...
    project_name = f"ID {project_id_str}"
    try:
        project_id = ObjectId(project_id_str)
        project = db.get_project(project_id)
        if project: project_name = project.get('name', project_name)
        deleted = db.delete_project(project_id)
        if deleted: flash(f"Project '{project_name}' and its tasks/logs deleted.", "success")
        else: flash(f"Project '{project_name}' could not be deleted.", "warning")
    except InvalidId: flash(f"Invalid Project ID format for deletion: {project_id_str}", "error")
    except ConnectionError as e: flash(f"Database error deleting project '{project_name}': {e}", "error")
    except Exception as e: print(f"--- ERROR (delete_project): {e} ---"); traceback.print_exc(); flash(f"Error deleting project '{project_name}': {e}", "error")
    return redirect(url_for('index'))

# == Tasks ==
@app.route('/tasks/add/<project_id_str>', methods=['POST'])
def add_task(project_id_str):
    # ... (keep implementation) ...
    task_name = request.form.get('name', 'Unknown Task')
    try:
        project_id = ObjectId(project_id_str)
        description = request.form.get('description', '')
        status = request.form.get('status', 'To Do'); priority = request.form.get('priority', 'Medium')
        due_date_str = request.form.get('due_date')
        due_date = datetime.datetime.strptime(due_date_str, DATE_FORMAT) if due_date_str else None
        est_hours_str = request.form.get('estimated_hours', '').strip()
        estimated_hours = float(est_hours_str) if est_hours_str else None
        if not task_name or not task_name.strip(): flash("Task name is required.", "error"); return redirect(url_for('index', project_id=project_id_str))
        if estimated_hours is not None and estimated_hours < 0: flash("Estimated hours cannot be negative.", "error"); return redirect(url_for('index', project_id=project_id_str))
        db.add_task(project_id=project_id, name=task_name.strip(), description=description, status=status, priority=priority, due_date=due_date, estimated_hours=estimated_hours)
        flash(f"Task '{task_name.strip()}' added.", "success")
    except InvalidId: flash(f"Invalid Project ID format when adding task: {project_id_str}", "error")
    except ValueError as ve: flash(f"Input Error adding task '{task_name}': {ve}", "error")
    except ConnectionError as e: flash(f"Database error adding task '{task_name}': {e}", "error")
    except Exception as e: print(f"--- ERROR (add_task): {e} ---"); traceback.print_exc(); flash(f"Error adding task '{task_name}': {e}", "error")
    return redirect(url_for('index', project_id=project_id_str))

# (Include placeholders or implementations for edit_task, delete_task, log_time)


# --- Run the App (Relevant only for direct `python app.py` execution) ---
if __name__ == '__main__':
    # This block is primarily for local development testing without Gunicorn/PM2
    debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'
    port = int(os.environ.get('PORT', 5000))

    # --- CHANGE HERE: Explicitly disable the reloader ---
    # The Flask reloader can conflict with PM2's process management.
    use_reloader = False
    # --- End Change ---

    print(f"--- Starting Flask app via app.run() [Development Server] ---")
    print(f"--- Config: host=0.0.0.0, port={port}, debug={debug_mode}, use_reloader={use_reloader} ---") # Log the setting
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=use_reloader)