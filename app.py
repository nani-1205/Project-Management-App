# app.py
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask.json.provider import DefaultJSONProvider

# --- Critical BSON Import Check ---
try:
    from bson import ObjectId, json_util
    from bson.errors import InvalidId
    print("--- Successfully imported ObjectId and json_util from bson ---")
    try:
        test_oid = ObjectId()
        # print(f"--- json_util test dump: {json_util.dumps({'test': test_oid})} ---") # Optional debug
    except Exception as e:
        print(f"--- ERROR: json_util failed test dump: {e} ---")
        sys.exit("Exiting: bson.json_util seems broken.")
except ImportError:
    print("--- ERROR: Failed to import ObjectId or json_util from bson. ---")
    sys.exit("Exiting: Required 'bson' components not found.")
# --- End BSON Import Check ---

import database as db
from config import APP_TITLE, get_options, DATE_FORMAT
import datetime
import json
import traceback

# --- Custom JSON Provider using BSON ---
class BSONJSONProvider(DefaultJSONProvider):
    """ Custom JSON Provider (primarily for jsonify) """
    def dumps(self, obj, **kwargs):
        try:
            # print(f"--- DEBUG: BSONJSONProvider.dumps called ---") # Optional debug
            return json_util.dumps(obj, **kwargs)
        except Exception as e:
            print(f"--- ERROR in BSONJSONProvider.dumps: {e} ---")
            raise
    def loads(self, s, **kwargs):
        # print(f"--- DEBUG: BSONJSONProvider.loads called ---") # Optional debug
        return json_util.loads(s, **kwargs)
# --- End Custom JSON Provider ---

# --- Flask App Setup ---
app = Flask(__name__)
app.json_provider_class = BSONJSONProvider
print(f"--- Flask App Created. JSON Provider set to: {app.json_provider_class.__name__} ---")
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
    return {'now': datetime.datetime.utcnow()}

# --- Filters for Jinja2 Templates ---
@app.template_filter('dateformat')
def dateformat(value, format=DATE_FORMAT):
    # ... (keep existing dateformat filter implementation) ...
    if value is None: return ""
    if isinstance(value, dict) and '$date' in value:
         try:
             ts_ms = value['$date']
             if isinstance(ts_ms, (int, float)): value = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
             else:
                 if str(ts_ms).endswith('Z'): ts_ms = str(ts_ms).replace('Z', '+00:00')
                 value = datetime.datetime.fromisoformat(str(ts_ms))
                 if value.tzinfo is None: value = value.replace(tzinfo=datetime.timezone.utc)
         except (ValueError, TypeError, KeyError) as e: print(f"--- WARNING: Error parsing date from BSON dict {value}: {e} ---"); return "Invalid Date"
    if isinstance(value, datetime.datetime): return value.strftime(format)
    if isinstance(value, str):
        try: return datetime.datetime.strptime(value, format).strftime(format)
        except ValueError: pass
    return str(value)


@app.template_filter('durationformat')
def durationformat(total_minutes):
     # ... (keep existing durationformat filter implementation) ...
    if total_minutes is None or not isinstance(total_minutes, (int, float)) or total_minutes < 0: return "N/A"
    total_minutes = int(total_minutes)
    if total_minutes == 0: return "0m"
    hours, minutes = divmod(total_minutes, 60)
    parts = []
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"

# --- NEW CUSTOM FILTER ---
@app.template_filter('bson_tojson')
def bson_to_json_filter(value):
    """Custom Jinja2 filter to dump BSON-containing objects to JSON string."""
    try:
        # Explicitly use bson.json_util.dumps
        return json_util.dumps(value)
    except Exception as e:
        print(f"--- ERROR in bson_to_json_filter for value type {type(value)}: {e} ---")
        # Return an empty JSON object string on error to prevent breaking template rendering
        return "{}"
# --- END NEW CUSTOM FILTER ---


# --- Web Routes ---
@app.route('/')
def index():
    # ... (keep existing index route implementation) ...
    selected_project_id_str = request.args.get('project_id')
    projects = []
    try: projects = db.get_projects(sort_by="name")
    except ConnectionError as e: flash(f"Database error fetching projects: {e}", "error"); return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)
    except Exception as e: print(f"--- ERROR (index): Fetching projects: {e} ---"); traceback.print_exc(); flash(f"Unexpected error fetching projects: {e}", "error"); return render_template('index.html', title=APP_TITLE, projects=[], tasks=[], selected_project=None, options=get_options(), error=True)

    selected_project = None
    tasks = []
    if selected_project_id_str:
        try:
            selected_project_id = ObjectId(selected_project_id_str)
            selected_project = db.get_project(selected_project_id)
            if selected_project: tasks = db.get_tasks_for_project(selected_project_id)
            else: flash(f"Project with ID {selected_project_id_str} not found.", "warning"); selected_project_id_str = None
        except InvalidId: flash(f"Invalid Project ID format: {selected_project_id_str}", "error"); selected_project_id_str = None
        except ConnectionError as e: flash(f"Database error fetching project/tasks: {e}", "error"); selected_project_id_str = None
        except Exception as e: print(f"--- ERROR (index): Loading project/tasks: {e} ---"); traceback.print_exc(); flash(f"Error loading project/tasks: {e}", "error"); selected_project_id_str = None

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
        flash(f"Error rendering page: {render_e}", "error")
        return "<h1>Internal Server Error</h1><p>Error rendering template. Check logs.</p>", 500


# --- API Routes ---
# (Keep existing API routes - jsonify should work fine with BSONJSONProvider)
@app.route('/api/projects/<project_id_str>/tasks')
def get_tasks_api(project_id_str):
    # ... implementation ...
     try:
        project_id = ObjectId(project_id_str)
        tasks = db.get_tasks_for_project(project_id)
        return jsonify(tasks) # Should use BSONJSONProvider
     except InvalidId: return jsonify({"error": "Invalid Project ID format"}), 400
     except ConnectionError as e: return jsonify({"error": f"Database connection error: {e}"}), 500
     except Exception as e: print(f"--- ERROR (get_tasks_api): {e} ---"); traceback.print_exc(); return jsonify({"error": "An unexpected error occurred"}), 500


# --- Form Handling Routes ---
# (Keep existing Project and Task CRUD routes)
# ... add_project, edit_project, delete_project, add_task ...

# --- Run the App (Only for direct `python app.py` execution) ---
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'
    port = int(os.environ.get('PORT', 5000))
    use_reloader = False # Keep reloader disabled when using PM2

    print(f"--- Starting Flask app via app.run() [Development Server] ---")
    print(f"--- Config: host=0.0.0.0, port={port}, debug={debug_mode}, use_reloader={use_reloader} ---")
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=use_reloader)