# app.py
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask.json.provider import DefaultJSONProvider

# --- BSON Import Check ---
try:
    from bson import ObjectId, json_util
    from bson.errors import InvalidId
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
# If jsonify works without it, you can remove this class and the app.json_provider_class line
class BSONJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        return json_util.dumps(obj, **kwargs)
    def loads(self, s, **kwargs):
        return json_util.loads(s, **kwargs)
# --- End Custom JSON Provider ---

# --- Flask App Setup ---
app = Flask(__name__)
# Uncomment next line if you want jsonify to automatically handle BSON types
# app.json_provider_class = BSONJSONProvider
# print(f"--- Flask App Created. JSON Provider set to: {app.json_provider_class.__name__} ---")
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
if not app.config['SECRET_KEY']:
    print("--- WARNING: FLASK_SECRET_KEY not set. Using random key (flash messages won't persist across restarts). ---")
# --- End Flask App Setup ---

# --- Database Connection Handling ---
try:
    db.connect_db()
except ConnectionError as e:
    print(f"--- FATAL: Could not connect to MongoDB on startup: {e} ---")

# --- Context Processor ---
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow()}

# --- Filters for Jinja2 Templates ---
@app.template_filter('dateformat')
def dateformat(value, format=DATE_FORMAT):
    """Formats a datetime object into a string for templates."""
    # (Keep improved implementation from previous attempts)
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
    if isinstance(value, str):
        try: return datetime.datetime.strptime(value, format).strftime(format)
        except ValueError: pass
    return str(value)

@app.template_filter('durationformat')
def durationformat(total_minutes):
    """Formats total minutes into Hh Mm format for templates."""
    # (Keep implementation from previous attempts)
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
    """Custom Jinja2 filter to dump BSON-containing objects to JSON string."""
    try:
        return json_util.dumps(value) # Use bson's utility
    except Exception as e:
        print(f"--- ERROR in bson_to_json_filter for value type {type(value)}: {e} ---")
        return "{}" # Return empty JSON on error

# --- Web Routes ---
@app.route('/')
def index():
    """Main page: Displays projects and tasks for a selected project."""
    selected_project_id_str = request.args.get('project_id')
    projects, tasks, selected_project = [], [], None
    try:
        projects = db.get_projects(sort_by="name")
        if selected_project_id_str:
            try:
                selected_project_id = ObjectId(selected_project_id_str)
                selected_project = db.get_project(selected_project_id)
                if selected_project:
                    tasks = db.get_tasks_for_project(selected_project_id)
                else:
                    flash(f"Project with ID {selected_project_id_str} not found.", "warning")
            except InvalidId:
                flash(f"Invalid Project ID format: {selected_project_id_str}", "error")
            except Exception as proj_e: # Catch errors loading specific project/tasks
                print(f"--- ERROR (index): Loading project/tasks {selected_project_id_str}: {proj_e} ---")
                traceback.print_exc()
                flash(f"Error loading project details: {proj_e}", "error")
    except ConnectionError as e:
        print(f"--- ERROR (index): Database connection error: {e} ---")
        flash(f"Database connection error: {e}", "error")
    except Exception as e:
        print(f"--- ERROR (index): Unexpected error: {e} ---")
        traceback.print_exc()
        flash(f"An unexpected server error occurred: {e}", "error")

    # Always attempt to render, even if data loading failed (flash messages will show)
    try:
        return render_template('index.html',
                               title=APP_TITLE,
                               projects=projects,
                               tasks=tasks,
                               selected_project=selected_project,
                               options=get_options())
    except Exception as render_e:
        print(f"--- ERROR (index): Exception during render_template: {render_e} ---")
        traceback.print_exc()
        # Return a simple error page if template rendering fails
        return "<h1>Internal Server Error</h1><p>Error rendering page content. Please check server logs.</p>", 500


# --- Form Handling Routes ---

# == Projects ==
@app.route('/projects/add', methods=['POST'])
def add_project():
    project_name = request.form.get('name', '')
    try:
        if not project_name or not project_name.strip():
            flash("Project name is required.", "error"); return redirect(url_for('index'))
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None
        if start_date and end_date and end_date < start_date:
             flash("End date cannot be earlier than start date.", "error"); return redirect(url_for('index'))
        new_id = db.add_project(
            name=project_name.strip(),
            description=request.form.get('description', ''),
            status=request.form.get('status', 'Planning'),
            start_date=start_date, end_date=end_date
        )
        flash(f"Project '{project_name.strip()}' added.", "success")
        return redirect(url_for('index', project_id=str(new_id)))
    except (ValueError, ConnectionError) as e:
        flash(f"Error adding project '{project_name}': {e}", "error")
    except Exception as e:
        print(f"--- ERROR (add_project): {e} ---"); traceback.print_exc()
        flash(f"Unexpected error adding project '{project_name}': {e}", "error")
    return redirect(url_for('index'))

@app.route('/projects/edit/<project_id_str>', methods=['POST'])
def edit_project(project_id_str):
    project_name_new = request.form.get('name', '')
    try:
        project_id = ObjectId(project_id_str)
        if not project_name_new or not project_name_new.strip():
            flash("Project name cannot be empty.", "error")
            return redirect(url_for('index', project_id=project_id_str))
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None
        if start_date and end_date and end_date < start_date:
             flash("End date cannot be earlier than start date.", "error")
             return redirect(url_for('index', project_id=project_id_str))
        updates = {
            "name": project_name_new.strip(),
            "description": request.form.get('description', ''),
            "status": request.form.get('status'),
            'start_date': start_date,
            'end_date': end_date
        }
        modified = db.update_project(project_id, updates)
        flash(f"Project '{updates['name']}' updated." if modified else "No changes detected.", "success" if modified else "info")
    except InvalidId:
        flash(f"Invalid Project ID: {project_id_str}", "error")
        return redirect(url_for('index'))
    except (ValueError, ConnectionError) as e:
        flash(f"Error updating project: {e}", "error")
    except Exception as e:
        print(f"--- ERROR (edit_project): {e} ---"); traceback.print_exc()
        flash(f"Unexpected error updating project: {e}", "error")
    return redirect(url_for('index', project_id=project_id_str)) # Redirect back

@app.route('/projects/delete/<project_id_str>', methods=['POST'])
def delete_project(project_id_str):
    project_name = f"ID {project_id_str}"
    try:
        project_id = ObjectId(project_id_str)
        project = db.get_project(project_id) # Get name before deleting
        if project: project_name = project.get('name', project_name)
        deleted = db.delete_project(project_id)
        flash(f"Project '{project_name}' deleted." if deleted else f"Project '{project_name}' not found or could not be deleted.", "success" if deleted else "warning")
    except InvalidId:
        flash(f"Invalid Project ID: {project_id_str}", "error")
    except (ValueError, ConnectionError) as e:
        flash(f"Error deleting project: {e}", "error")
    except Exception as e:
        print(f"--- ERROR (delete_project): {e} ---"); traceback.print_exc()
        flash(f"Unexpected error deleting project: {e}", "error")
    return redirect(url_for('index'))

# == Tasks ==
@app.route('/tasks/add/<project_id_str>', methods=['POST'])
def add_task(project_id_str):
    task_name = request.form.get('name', '')
    try:
        project_id = ObjectId(project_id_str)
        if not task_name or not task_name.strip():
            flash("Task name is required.", "error")
            return redirect(url_for('index', project_id=project_id_str))
        due_date_str = request.form.get('due_date')
        due_date = datetime.datetime.strptime(due_date_str, DATE_FORMAT) if due_date_str else None
        est_hours_str = request.form.get('estimated_hours', '').strip()
        estimated_hours = float(est_hours_str) if est_hours_str else None
        if estimated_hours is not None and estimated_hours < 0:
             flash("Estimated hours cannot be negative.", "error")
             return redirect(url_for('index', project_id=project_id_str))
        db.add_task(
            project_id=project_id, name=task_name.strip(),
            description=request.form.get('description', ''),
            status=request.form.get('status', 'To Do'),
            priority=request.form.get('priority', 'Medium'),
            due_date=due_date, estimated_hours=estimated_hours
        )
        flash(f"Task '{task_name.strip()}' added.", "success")
    except InvalidId:
        flash(f"Invalid Project ID: {project_id_str}", "error")
    except (ValueError, ConnectionError) as e:
        flash(f"Error adding task: {e}", "error")
    except Exception as e:
        print(f"--- ERROR (add_task): {e} ---"); traceback.print_exc()
        flash(f"Unexpected error adding task: {e}", "error")
    return redirect(url_for('index', project_id=project_id_str))

# (Add placeholders/implementations for edit_task, delete_task, log_time)

# --- Run the App (Only for direct `python app.py` execution) ---
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'
    port = int(os.environ.get('PORT', 5000))
    # --- IMPORTANT: Keep reloader disabled when using PM2 ---
    use_reloader = False
    # ---
    print(f"--- Starting Flask app via app.run() [Development Server] ---")
    print(f"--- Config: host=0.0.0.0, port={port}, debug={debug_mode}, use_reloader={use_reloader} ---")
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=use_reloader)