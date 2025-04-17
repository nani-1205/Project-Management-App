# project_tracker/ui/app_window.py
import customtkinter as ctk
from ui.project_frame import ProjectFrame
from ui.task_frame import TaskFrame
import database as db
from config import APP_TITLE, THEME, COLOR_THEME
from ui.utils import show_error

class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1100x600") # Adjust size as needed

        ctk.set_appearance_mode(THEME)
        ctk.set_default_color_theme(COLOR_THEME)

        # --- Main Layout ---
        self.grid_columnconfigure(1, weight=1) # Task frame expands
        self.grid_rowconfigure(0, weight=1)

        # --- Check DB Connection on Startup ---
        try:
            db.connect_db() # Establish connection early
        except ConnectionError as e:
             show_error("Database Connection Error", f"Failed to connect to MongoDB:\n{e}\n\nPlease ensure MongoDB is running and the connection string in config.py or .env is correct.\nApplication will exit.")
             self.after(100, self.destroy) # Schedule exit after message box closes
             return # Stop further initialization

        # --- App Callbacks ---
        # Used for communication between frames (e.g., project selection -> task loading)
        app_callbacks = {
            'on_project_selected': self.on_project_selected,
            'on_project_deselected': self.on_project_deselected,
        }

        # --- Left Sidebar (Projects) ---
        self.project_sidebar = ProjectFrame(self, app_callbacks=app_callbacks, width=250)
        self.project_sidebar.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")

        # --- Right Main Area (Tasks) ---
        self.task_area = TaskFrame(self)
        self.task_area.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

    def on_project_selected(self, project_id):
        """Callback when a project is selected in the ProjectFrame."""
        project_data = self.project_sidebar.projects.get(project_id)
        if project_data:
            self.task_area.load_tasks(project_id, project_data.get('name', 'Unknown Project'))
        else:
            show_error("Error", "Could not find data for the selected project.")
            self.task_area.clear_tasks()

    def on_project_deselected(self):
        """Callback when project selection is cleared."""
        self.task_area.clear_tasks()

    def run(self):
        """Starts the Tkinter main loop."""
        self.mainloop()