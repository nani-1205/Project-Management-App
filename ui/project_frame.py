# project_tracker/ui/project_frame.py
import customtkinter as ctk
from ui.dialogs import ProjectDialog
from ui.utils import show_error, show_info, ask_yes_no, format_date
import database as db # Use alias for clarity

class ProjectFrame(ctk.CTkFrame):
    def __init__(self, master, app_callbacks, **kwargs):
        super().__init__(master, **kwargs)
        self.app_callbacks = app_callbacks # To notify main app of selection changes
        self.projects = {} # Dictionary to store project data by ID
        self.selected_project_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Title and Buttons ---
        self.title_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.title_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.title_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.title_frame, text="Projects", font=ctk.CTkFont(size=16, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")

        self.add_button = ctk.CTkButton(self.title_frame, text="+ Add", width=60, command=self.add_project)
        self.add_button.grid(row=0, column=1, padx=(5, 0))

        self.edit_button = ctk.CTkButton(self.title_frame, text="Edit", width=60, command=self.edit_project, state="disabled")
        self.edit_button.grid(row=0, column=2, padx=(5, 0))

        self.delete_button = ctk.CTkButton(self.title_frame, text="Del", width=50, command=self.delete_project, state="disabled", fg_color="red", hover_color="darkred")
        self.delete_button.grid(row=0, column=3, padx=(5, 0))

        # --- Project List ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color=self.cget('fg_color')) # Match frame background
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.project_widgets = {} # Keep track of button/label widgets for selection styling {project_id: widget}

        self.load_projects()

    def load_projects(self):
        """Loads projects from DB and displays them."""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.project_widgets.clear()
        self.projects.clear()
        self.selected_project_id = None
        self._update_button_states()

        try:
            projects_data = db.get_projects(sort_by="name")
            for project in projects_data:
                project_id = project['_id']
                self.projects[project_id] = project # Store full data

                proj_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent", cursor="hand2")
                proj_frame.pack(fill="x", pady=(0, 2))
                proj_frame.bind("<Button-1>", lambda event, pid=project_id: self.select_project(pid))

                name_label = ctk.CTkLabel(proj_frame, text=project['name'], anchor="w", padx=5)
                name_label.pack(fill="x")
                name_label.bind("<Button-1>", lambda event, pid=project_id: self.select_project(pid))

                self.project_widgets[project_id] = proj_frame # Use frame for bg change

        except Exception as e:
            show_error("Database Error", f"Failed to load projects: {e}")

        # If there was a selection before reload, try to reselect
        # if self.selected_project_id and self.selected_project_id in self.projects:
        #     self.select_project(self.selected_project_id)
        # else:
        #     self.deselect_project() # Ensure buttons are disabled if no selection


    def select_project(self, project_id):
        """Handles selecting a project in the list."""
        if self.selected_project_id == project_id:
            return # Already selected

        # Deselect previous
        if self.selected_project_id and self.selected_project_id in self.project_widgets:
             widget = self.project_widgets[self.selected_project_id]
             widget.configure(fg_color="transparent") # Reset background

        # Select new
        self.selected_project_id = project_id
        widget = self.project_widgets[project_id]
        widget.configure(fg_color=("gray70", "gray30")) # Highlight selected

        self._update_button_states()

        # Notify the main application
        if self.app_callbacks.get('on_project_selected'):
            self.app_callbacks['on_project_selected'](project_id)

    def deselect_project(self):
        """Clears the current selection."""
        if self.selected_project_id and self.selected_project_id in self.project_widgets:
             widget = self.project_widgets[self.selected_project_id]
             widget.configure(fg_color="transparent") # Reset background
        self.selected_project_id = None
        self._update_button_states()
        # Notify the main application
        if self.app_callbacks.get('on_project_deselected'):
            self.app_callbacks['on_project_deselected']()


    def _update_button_states(self):
        """Enables/disables edit and delete buttons based on selection."""
        state = "normal" if self.selected_project_id else "disabled"
        self.edit_button.configure(state=state)
        self.delete_button.configure(state=state)

    def add_project(self):
        """Opens dialog to add a new project."""
        dialog = ProjectDialog(self, title="Add New Project")
        if dialog.result:
            try:
                new_id = db.add_project(**dialog.result)
                show_info("Success", f"Project '{dialog.result['name']}' added.")
                self.load_projects()
                # Optionally auto-select the newly added project
                self.select_project(new_id)
            except Exception as e:
                show_error("Database Error", f"Failed to add project: {e}")

    def edit_project(self):
        """Opens dialog to edit the selected project."""
        if not self.selected_project_id:
            return

        project_data = self.projects.get(self.selected_project_id)
        if not project_data:
            show_error("Error", "Selected project data not found.")
            self.load_projects() # Reload to fix inconsistency
            return

        dialog = ProjectDialog(self, title="Edit Project", project_data=project_data)
        if dialog.result:
            try:
                updated = db.update_project(self.selected_project_id, dialog.result)
                if updated:
                    show_info("Success", f"Project '{dialog.result['name']}' updated.")
                    # Store updated data locally before reloading list (optional)
                    self.projects[self.selected_project_id].update(dialog.result)
                    # Update the displayed name immediately if it changed
                    widget = self.project_widgets[self.selected_project_id]
                    # Assuming the label is the first child of the frame
                    if widget and widget.winfo_children():
                        label = widget.winfo_children()[0]
                        label.configure(text=dialog.result['name'])
                    # No full reload needed unless sorting changes
                    # self.load_projects() # Optionally reload full list
                    # Refresh task view if project details changed affect it
                    if self.app_callbacks.get('on_project_selected'):
                        self.app_callbacks['on_project_selected'](self.selected_project_id)
                else:
                    show_info("Info", "No changes detected for the project.")
            except Exception as e:
                show_error("Database Error", f"Failed to update project: {e}")

    def delete_project(self):
        """Deletes the selected project after confirmation."""
        if not self.selected_project_id:
            return

        project_name = self.projects.get(self.selected_project_id, {}).get('name', 'this project')
        if ask_yes_no("Confirm Delete", f"Are you sure you want to delete '{project_name}' and ALL its associated tasks and time logs?"):
            try:
                deleted = db.delete_project(self.selected_project_id)
                if deleted:
                    show_info("Success", f"Project '{project_name}' deleted.")
                    # Important: Deselect before reloading
                    original_selection = self.selected_project_id
                    self.deselect_project() # Clears selection and notifies app
                    self.load_projects() # Reload project list
                else:
                    show_error("Error", "Project could not be found or deleted.")
                    self.load_projects() # Reload to sync
            except Exception as e:
                show_error("Database Error", f"Failed to delete project: {e}")