# project_tracker/ui/task_frame.py
import customtkinter as ctk
from ui.dialogs import TaskDialog, TimeLogDialog
from ui.utils import show_error, show_info, ask_yes_no, format_date, format_duration, format_datetime
import database as db

class TaskFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.current_project_id = None
        self.current_project_name = "No Project Selected"
        self.tasks = {} # Store task data by ID {task_id: task_data}
        self.selected_task_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Allow task list to expand

        # --- Title and Buttons ---
        self.title_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.title_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.title_frame.grid_columnconfigure(0, weight=1) # Make label expand

        self.title_label = ctk.CTkLabel(self.title_frame, text=f"Tasks for: {self.current_project_name}", font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
        self.title_label.grid(row=0, column=0, sticky="ew")

        self.add_button = ctk.CTkButton(self.title_frame, text="+ Add Task", width=80, command=self.add_task, state="disabled")
        self.add_button.grid(row=0, column=1, padx=(5, 0))

        self.edit_button = ctk.CTkButton(self.title_frame, text="Edit", width=60, command=self.edit_task, state="disabled")
        self.edit_button.grid(row=0, column=2, padx=(5, 0))

        self.log_time_button = ctk.CTkButton(self.title_frame, text="Log Time", width=80, command=self.log_time, state="disabled")
        self.log_time_button.grid(row=0, column=3, padx=(5, 0))

        self.delete_button = ctk.CTkButton(self.title_frame, text="Del", width=50, command=self.delete_task, state="disabled", fg_color="red", hover_color="darkred")
        self.delete_button.grid(row=0, column=4, padx=(5, 0))


        # --- Task List Header ---
        self.header_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray20"), height=25) # Header background
        self.header_frame.grid(row=1, column=0, padx=10, pady=(5,0), sticky="new")
        self.header_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1) # Distribute space

        # Define headers (adjust text/weights as needed)
        headers = [("Name", 3), ("Status", 1), ("Priority", 1), ("Due Date", 1), ("Logged", 1), ("Est.", 1)]
        for i, (text, weight) in enumerate(headers):
            self.header_frame.grid_columnconfigure(i, weight=weight)
            lbl = ctk.CTkLabel(self.header_frame, text=text, font=ctk.CTkFont(weight="bold"), anchor="w", padx=5)
            lbl.grid(row=0, column=i, sticky="ew")


        # --- Task List ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color=self.cget('fg_color'))
        self.scrollable_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.task_widgets = {} # {task_id: frame_widget}

        # Placeholder when no project is selected
        self.no_project_label = ctk.CTkLabel(self, text="Select a project to view its tasks.", text_color="gray")
        # self.no_project_label.place(relx=0.5, rely=0.5, anchor="center") # Initially centered, will be hidden

    def load_tasks(self, project_id, project_name="Selected Project"):
        """Loads tasks for the given project ID."""
        self.current_project_id = project_id
        self.current_project_name = project_name
        self.title_label.configure(text=f"Tasks for: {self.current_project_name}")
        self.selected_task_id = None

        # Hide placeholder, show headers and list
        # self.no_project_label.place_forget()
        self.header_frame.grid()
        self.scrollable_frame.grid()

        # Clear existing task widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.task_widgets.clear()
        self.tasks.clear()

        if not project_id:
            self.clear_tasks() # Handle case where project becomes invalid
            return

        try:
            tasks_data = db.get_tasks_for_project(project_id, sort_by="priority") # Or sort by name, status etc.
            for task in tasks_data:
                task_id = task['_id']
                self.tasks[task_id] = task
                self._add_task_widget(task)

            self.add_button.configure(state="normal") # Enable Add Task button

        except Exception as e:
            show_error("Database Error", f"Failed to load tasks for project {project_name}: {e}")
            self.clear_tasks() # Clear display on error

        self._update_button_states()


    def _add_task_widget(self, task):
        """Creates and adds the widget row for a single task."""
        task_id = task['_id']

        task_row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent", cursor="hand2")
        task_row_frame.pack(fill="x", pady=(0, 1), padx=1)
        task_row_frame.bind("<Button-1>", lambda event, tid=task_id: self.select_task(tid))

        # Use the same weights as the header
        columns_data = [
            (task.get('name', 'N/A'), 3),
            (task.get('status', 'N/A'), 1),
            (task.get('priority', 'N/A'), 1),
            (format_date(task.get('due_date')), 1),
            (format_duration(task.get('total_logged_minutes', 0)), 1),
            (f"{task.get('estimated_hours', 'N/A')}h" if task.get('estimated_hours') is not None else "N/A", 1)
        ]

        for i, (text, weight) in enumerate(columns_data):
            task_row_frame.grid_columnconfigure(i, weight=weight)
            lbl = ctk.CTkLabel(task_row_frame, text=text, anchor="w", padx=5)
            lbl.grid(row=0, column=i, sticky="ew")
            lbl.bind("<Button-1>", lambda event, tid=task_id: self.select_task(tid)) # Bind label too

        self.task_widgets[task_id] = task_row_frame


    def select_task(self, task_id):
        """Highlights the selected task row."""
        if self.selected_task_id == task_id:
             return # Already selected

        # Deselect previous
        if self.selected_task_id and self.selected_task_id in self.task_widgets:
             widget = self.task_widgets[self.selected_task_id]
             widget.configure(fg_color="transparent")

        # Select new
        self.selected_task_id = task_id
        if task_id in self.task_widgets:
            widget = self.task_widgets[task_id]
            widget.configure(fg_color=("gray70", "gray30")) # Highlight

        self._update_button_states()

    def deselect_task(self):
         """Clears the current task selection."""
         if self.selected_task_id and self.selected_task_id in self.task_widgets:
             widget = self.task_widgets[self.selected_task_id]
             widget.configure(fg_color="transparent")
         self.selected_task_id = None
         self._update_button_states()


    def clear_tasks(self):
        """Clears the task list and resets the state."""
        self.current_project_id = None
        self.current_project_name = "No Project Selected"
        self.title_label.configure(text=f"Tasks for: {self.current_project_name}")
        self.selected_task_id = None
        self.tasks.clear()

        # Clear existing task widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.task_widgets.clear()

        # Hide headers and list, show placeholder
        self.header_frame.grid_remove()
        self.scrollable_frame.grid_remove()
        # self.no_project_label.place(relx=0.5, rely=0.5, anchor="center")

        self.add_button.configure(state="disabled")
        self._update_button_states() # Disables edit/delete/log time

    def _update_button_states(self):
        """Updates states of edit, delete, log time buttons based on task selection."""
        task_selected = self.selected_task_id is not None
        state = "normal" if task_selected else "disabled"
        self.edit_button.configure(state=state)
        self.delete_button.configure(state=state)
        self.log_time_button.configure(state=state)
        # Add task button depends only on project selection
        self.add_button.configure(state="normal" if self.current_project_id else "disabled")

    def add_task(self):
        """Opens dialog to add a new task to the current project."""
        if not self.current_project_id:
            show_error("Error", "Please select a project first.")
            return

        dialog = TaskDialog(self, title=f"Add Task to {self.current_project_name}")
        if dialog.result:
            try:
                new_id = db.add_task(self.current_project_id, **dialog.result)
                show_info("Success", f"Task '{dialog.result['name']}' added.")
                # Reload tasks for the current project to show the new one
                self.load_tasks(self.current_project_id, self.current_project_name)
                # Optional: select the new task
                self.select_task(new_id)
            except Exception as e:
                show_error("Database Error", f"Failed to add task: {e}")

    def edit_task(self):
        """Opens dialog to edit the selected task."""
        if not self.selected_task_id: return

        task_data = self.tasks.get(self.selected_task_id)
        if not task_data:
            show_error("Error", "Selected task data not found.")
            self.load_tasks(self.current_project_id, self.current_project_name) # Reload
            return

        dialog = TaskDialog(self, title="Edit Task", task_data=task_data)
        if dialog.result:
            try:
                updated = db.update_task(self.selected_task_id, dialog.result)
                if updated:
                    show_info("Success", f"Task '{dialog.result['name']}' updated.")
                    # Reload tasks to show changes
                    self.load_tasks(self.current_project_id, self.current_project_name)
                    # Re-select the edited task if needed
                    self.select_task(self.selected_task_id)
                else:
                    show_info("Info", "No changes detected for the task.")
            except Exception as e:
                show_error("Database Error", f"Failed to update task: {e}")

    def delete_task(self):
        """Deletes the selected task after confirmation."""
        if not self.selected_task_id: return

        task_name = self.tasks.get(self.selected_task_id, {}).get('name', 'this task')
        if ask_yes_no("Confirm Delete", f"Are you sure you want to delete task '{task_name}' and its time logs?"):
            try:
                deleted = db.delete_task(self.selected_task_id)
                if deleted:
                    show_info("Success", f"Task '{task_name}' deleted.")
                    # Reload tasks for the current project
                    self.load_tasks(self.current_project_id, self.current_project_name)
                    # Selection is implicitly cleared by load_tasks
                else:
                    show_error("Error", "Task could not be found or deleted.")
                    self.load_tasks(self.current_project_id, self.current_project_name) # Reload
            except Exception as e:
                show_error("Database Error", f"Failed to delete task: {e}")


    def log_time(self):
        """Opens dialog to log time for the selected task."""
        if not self.selected_task_id: return

        task_name = self.tasks.get(self.selected_task_id, {}).get('name', 'Selected Task')
        dialog = TimeLogDialog(self, title=f"Log Time for: {task_name}")

        if dialog.result:
            try:
                db.add_time_log(self.selected_task_id, **dialog.result)
                show_info("Success", f"Time logged for task '{task_name}'.")
                # Reload tasks to update the 'Logged' column
                self.load_tasks(self.current_project_id, self.current_project_name)
                # Re-select the task
                self.select_task(self.selected_task_id)
            except ValueError as ve: # Catch specific validation errors from db layer
                show_error("Input Error", str(ve))
            except Exception as e:
                 show_error("Database Error", f"Failed to log time: {e}")

    def refresh_task_display(self, task_id):
        """Updates the display of a single task row without reloading all."""
        if task_id not in self.tasks or task_id not in self.task_widgets:
             return # Task not currently displayed or data missing

        task_data = self.tasks.get(task_id)
        widget_frame = self.task_widgets.get(task_id)
        if not task_data or not widget_frame: return

        # Get all label widgets within the frame
        labels = widget_frame.winfo_children()
        if len(labels) >= 6: # Ensure we have the expected number of labels
            try:
                # Update labels based on new data (indexes match _add_task_widget)
                labels[0].configure(text=task_data.get('name', 'N/A'))
                labels[1].configure(text=task_data.get('status', 'N/A'))
                labels[2].configure(text=task_data.get('priority', 'N/A'))
                labels[3].configure(text=format_date(task_data.get('due_date')))
                labels[4].configure(text=format_duration(task_data.get('total_logged_minutes', 0)))
                labels[5].configure(text=f"{task_data.get('estimated_hours', 'N/A')}h" if task_data.get('estimated_hours') is not None else "N/A")
            except Exception as e:
                print(f"Error updating task widget: {e}") # Log potential Tkinter errors
                # Fallback to full reload if partial update fails
                self.load_tasks(self.current_project_id, self.current_project_name)
                self.select_task(task_id)