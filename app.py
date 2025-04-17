# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from bson import ObjectId, json_util # Import json_util for better serialization
import database as db
from config import APP_TITLE, get_options, DATE_FORMAT
import datetime
import json # Import Python's json module

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Needed for flash messages

# --- Database Connection Handling ---
# Try to connect at startup
try:
    db.connect_db()
except ConnectionError as e:
    print(f"FATAL: Could not connect to MongoDB on startup: {e}")
    # In a real app, you might have more robust handling here
    # For now, it will likely crash later when a route tries db.get_db()

# --- Utility for JSON serialization ---
def parse_json(data):
    # Use json_util to handle MongoDB specific types like ObjectId and datetime
    return json.loads(json_util.dumps(data))

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
        # Check if a project is pre-selected via query parameter
        selected_project_id_str = request.args.get('project_id')
        selected_project = None
        tasks = []
        if selected_project_id_str:
            try:
                selected_project = db.get_project(ObjectId(selected_project_id_str))
                if selected_project:
                    tasks = db.get_tasks_for_project(selected_project['_id'])
                else:
                     flash(f"Project with ID {selected_project_id_str} not found.", "warning")
                     selected_project_id_str = None # Clear selection if not found
            except Exception as e:
                 flash(f"Error loading selected project or tasks: {e}", "error")
                 selected_project_id_str = None # Clear selection on error

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
        print(f"ERROR in index route: {e}")
        return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)


# --- API Routes (for JavaScript interaction) ---

@app.route('/api/projects/<project_id_str>/tasks')
def get_tasks_api(project_id_str):
    """API endpoint to get tasks for a project."""
    try:
        project_id = ObjectId(project_id_str)
        tasks = db.get_tasks_for_project(project_id)
        return jsonify(parse_json(tasks)) # Use parse_json helper
    except Exception as e:
        # Log error
        print(f"ERROR in get_tasks_api for {project_id_str}: {e}")
        return jsonify({"error": str(e)}), 400

# --- Form Handling Routes ---

# == Projects ==
@app.route('/projects/add', methods=['POST'])
def add_project():
    """Handles adding a new project via form submission."""
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        status = request.form.get('status', 'Planning')
        # Handle dates (convert empty strings to None)
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None

        if not name:
            flash("Project name is required.", "error")
            return redirect(url_for('index'))

        new_id = db.add_project(name=name, description=description, status=status, start_date=start_date, end_date=end_date)
        flash(f"Project '{name}' added successfully.", "success")
        return redirect(url_for('index', project_id=str(new_id))) # Redirect to show the new project selected
    except Exception as e:
        flash(f"Error adding project: {e}", "error")
        print(f"ERROR adding project: {e}")
        return redirect(url_for('index'))

@app.route('/projects/edit/<project_id_str>', methods=['POST'])
def edit_project(project_id_str):
    """Handles editing an existing project."""
    try:
        project_id = ObjectId(project_id_str)
        updates = {
            "name": request.form.get('name'),
            "description": request.form.get('description', ''),
            "status": request.form.get('status'),
        }
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        updates['start_date'] = datetime.datetime.strptime(start_date_str, DATE_FORMAT) if start_date_str else None
        updates['end_date'] = datetime.datetime.strptime(end_date_str, DATE_FORMAT) if end_date_str else None

        if not updates["name"]:
            flash("Project name cannot be empty.", "error")
            # Pass current project_id back to keep it selected
            return redirect(url_for('index', project_id=project_id_str))

        modified = db.update_project(project_id, updates)
        if modified:
            flash(f"Project '{updates['name']}' updated.", "success")
        else:
            flash("No changes detected for the project.", "info")
        return redirect(url_for('index', project_id=project_id_str)) # Keep project selected
    except Exception as e:
        flash(f"Error updating project: {e}", "error")
        print(f"ERROR updating project {project_id_str}: {e}")
        # Redirect to main page if update fails badly
        return redirect(url_for('index', project_id=project_id_str))


@app.route('/projects/delete/<project_id_str>', methods=['POST']) # Use POST for delete actions
def delete_project(project_id_str):
    """Handles deleting a project."""
    try:
        project_id = ObjectId(project_id_str)
        project = db.get_project(project_id) # Get name for flash message
        project_name = project['name'] if project else 'the project'

        deleted = db.delete_project(project_id)
        if deleted:
            flash(f"Project '{project_name}' and its tasks deleted.", "success")
        else:
            flash("Project could not be deleted (maybe it was already removed?).", "warning")
        return redirect(url_for('index')) # Go back to main list
    except Exception as e:
        flash(f"Error deleting project: {e}", "error")
        print(f"ERROR deleting project {project_id_str}: {e}")
        return redirect(url_for('index', project_id=project_id_str)) # Keep selection if delete failed


# == Tasks ==
@app.route('/tasks/add/<project_id_str>', methods=['POST'])
def add_task(project_id_str):
    """Handles adding a new task."""
    try:
        project_id = ObjectId(project_id_str)
        name = request.form.get('name')
        description = request.form.get('description', '')
        status = request.form.get('status', 'To Do')
        priority = request.form.get('priority', 'Medium')
        due_date_str = request.form.get('due_date')
        due_date = datetime.datetime.strptime(due_date_str, DATE_FORMAT) if due_date_str else None
        est_hours_str = request.form.get('estimated_hours').strip()
        estimated_hours = float(est_hours_str) if est_hours_str else None

        if not name:
            flash("Task name is required.", "error")
            return redirect(url_for('index', project_id=project_id_str))

        db.add_task(project_id=project_id, name=name, description=description,
                    status=status, priority=priority, due_date=due_date,
                    estimated_hours=estimated_hours)
        flash(f"Task '{name}' added.", "success")
    except ValueError as ve:
         flash(f"Input Error adding task: {ve}", "error")
    except Exception as e:
        flash(f"Error adding task: {e}", "error")
        print(f"ERROR adding task to project {project_id_str}: {e}")

    return redirect(url_for('index', project_id=project_id_str)) # Redirect back to the project

# Add routes for editing and deleting tasks similarly...
# (Left as an exercise - follow the pattern for projects)

# Add routes for adding/viewing time logs...
# (Left as an exercise)


# --- Run the App ---
if __name__ == '__main__':
    # Use 0.0.0.0 to make it accessible on your network
    # Debug=True is helpful during development (auto-reloads),
    # BUT **NEVER** use debug=True in production!
    app.run(host='0.0.0.0', port=5000, debug=True)