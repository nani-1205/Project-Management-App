# project_tracker/ui/dialogs.py
import customtkinter as ctk
from tkinter import simpledialog, messagebox
import datetime
from tkcalendar import DateEntry # Needs pip install tkcalendar
from config import (PROJECT_STATUS_OPTIONS, TASK_STATUS_OPTIONS,
                    TASK_PRIORITY_OPTIONS, DATE_FORMAT)
from ui.utils import parse_date

# --- Base Dialog ---
class BaseDialog(ctk.CTkToplevel):
    """Base class for modal dialogs."""
    def __init__(self, parent, title="Dialog"):
        super().__init__(parent)
        self.title(title)
        self.parent = parent
        self.result = None # Store the result of the dialog

        self.transient(parent) # Keep dialog on top of parent
        self.grab_set() # Make dialog modal
        self.protocol("WM_DELETE_WINDOW", self._on_cancel) # Handle closing window

        # Center the dialog relative to the parent
        self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        self._create_widgets()
        self._create_buttons()

        self.lift() # Bring window to the front
        self.focus_set() # Set focus to the dialog
        self.wait_window(self) # Wait until window is destroyed

    def _create_widgets(self):
        """Placeholder for creating specific dialog widgets."""
        raise NotImplementedError

    def _create_buttons(self):
        """Creates standard OK/Cancel buttons."""
        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(pady=(10, 0), fill="x")

        self.ok_button = ctk.CTkButton(button_frame, text="OK", command=self._on_ok, width=80)
        self.ok_button.pack(side="right", padx=(10, 0))

        self.cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self._on_cancel, width=80, fg_color="gray")
        self.cancel_button.pack(side="right")

    def _on_ok(self):
        """Handles OK button click. Validation should happen here."""
        if self._validate_input():
            self.result = self._get_values()
            self.destroy() # Close the dialog

    def _on_cancel(self):
        """Handles Cancel button click or window close."""
        self.result = None
        self.destroy()

    def _validate_input(self):
        """Placeholder for input validation. Return True if valid."""
        return True

    def _get_values(self):
        """Placeholder for returning data entered in the dialog."""
        raise NotImplementedError


# --- Project Dialog ---
class ProjectDialog(BaseDialog):
    def __init__(self, parent, title="Project Details", project_data=None):
        self.project_data = project_data or {} # Existing data for editing
        super().__init__(parent, title)

    def _create_widgets(self):
        # Name
        ctk.CTkLabel(self.main_frame, text="Project Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = ctk.CTkEntry(self.main_frame, width=300)
        self.name_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        self.name_entry.insert(0, self.project_data.get("name", ""))

        # Description
        ctk.CTkLabel(self.main_frame, text="Description:").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        self.desc_textbox = ctk.CTkTextbox(self.main_frame, height=80, width=300)
        self.desc_textbox.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        self.desc_textbox.insert("1.0", self.project_data.get("description", ""))

        # Status
        ctk.CTkLabel(self.main_frame, text="Status:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.status_var = ctk.StringVar(value=self.project_data.get("status", PROJECT_STATUS_OPTIONS[0]))
        self.status_menu = ctk.CTkOptionMenu(self.main_frame, variable=self.status_var, values=PROJECT_STATUS_OPTIONS)
        self.status_menu.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Dates (Using tkcalendar DateEntry)
        ctk.CTkLabel(self.main_frame, text="Start Date:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        start_date_val = self.project_data.get("start_date")
        self.start_date_entry = DateEntry(self.main_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern=DATE_FORMAT.lower()) # tkcalendar uses lowercase date codes
        self.start_date_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        if start_date_val: self.start_date_entry.set_date(start_date_val)
        else: self.start_date_entry.delete(0, 'end') # Clear default date

        ctk.CTkLabel(self.main_frame, text="End Date:").grid(row=3, column=2, padx=5, pady=5, sticky="w")
        end_date_val = self.project_data.get("end_date")
        self.end_date_entry = DateEntry(self.main_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern=DATE_FORMAT.lower())
        self.end_date_entry.grid(row=3, column=3, padx=5, pady=5, sticky="w")
        if end_date_val: self.end_date_entry.set_date(end_date_val)
        else: self.end_date_entry.delete(0, 'end') # Clear default date

        self.main_frame.columnconfigure(1, weight=1) # Allow entry/textbox to expand


    def _validate_input(self):
        name = self.name_entry.get().strip()
        if not name:
            show_error("Input Error", "Project name cannot be empty.")
            return False
        # Optional: Validate date logic (end date >= start date)
        start_dt = parse_date(self.start_date_entry.get())
        end_dt = parse_date(self.end_date_entry.get())
        if start_dt and end_dt and end_dt < start_dt:
            show_error("Input Error", "End date cannot be earlier than start date.")
            return False
        return True

    def _get_values(self):
        start_date = parse_date(self.start_date_entry.get())
        end_date = parse_date(self.end_date_entry.get())

        return {
            "name": self.name_entry.get().strip(),
            "description": self.desc_textbox.get("1.0", "end-1c").strip(),
            "status": self.status_var.get(),
            "start_date": start_date,
            "end_date": end_date
        }

# --- Task Dialog ---
class TaskDialog(BaseDialog):
    def __init__(self, parent, title="Task Details", task_data=None):
        self.task_data = task_data or {}
        super().__init__(parent, title)

    def _create_widgets(self):
        # Name
        ctk.CTkLabel(self.main_frame, text="Task Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = ctk.CTkEntry(self.main_frame, width=300)
        self.name_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        self.name_entry.insert(0, self.task_data.get("name", ""))

        # Description
        ctk.CTkLabel(self.main_frame, text="Description:").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        self.desc_textbox = ctk.CTkTextbox(self.main_frame, height=60, width=300)
        self.desc_textbox.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        self.desc_textbox.insert("1.0", self.task_data.get("description", ""))

        # Status
        ctk.CTkLabel(self.main_frame, text="Status:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.status_var = ctk.StringVar(value=self.task_data.get("status", TASK_STATUS_OPTIONS[0]))
        self.status_menu = ctk.CTkOptionMenu(self.main_frame, variable=self.status_var, values=TASK_STATUS_OPTIONS)
        self.status_menu.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Priority
        ctk.CTkLabel(self.main_frame, text="Priority:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.priority_var = ctk.StringVar(value=self.task_data.get("priority", TASK_PRIORITY_OPTIONS[1])) # Default Medium
        self.priority_menu = ctk.CTkOptionMenu(self.main_frame, variable=self.priority_var, values=TASK_PRIORITY_OPTIONS)
        self.priority_menu.grid(row=2, column=3, padx=5, pady=5, sticky="w")

        # Due Date
        ctk.CTkLabel(self.main_frame, text="Due Date:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        due_date_val = self.task_data.get("due_date")
        self.due_date_entry = DateEntry(self.main_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern=DATE_FORMAT.lower())
        self.due_date_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        if due_date_val: self.due_date_entry.set_date(due_date_val)
        else: self.due_date_entry.delete(0, 'end') # Clear default date

        # Estimated Hours
        ctk.CTkLabel(self.main_frame, text="Est. Hours:").grid(row=3, column=2, padx=5, pady=5, sticky="w")
        self.est_hours_entry = ctk.CTkEntry(self.main_frame, width=80)
        self.est_hours_entry.grid(row=3, column=3, padx=5, pady=5, sticky="w")
        est_hours = self.task_data.get("estimated_hours")
        self.est_hours_entry.insert(0, str(est_hours) if est_hours is not None else "")

        self.main_frame.columnconfigure(1, weight=1)

    def _validate_input(self):
        name = self.name_entry.get().strip()
        if not name:
            show_error("Input Error", "Task name cannot be empty.")
            return False

        # Validate estimated hours is a number (or empty)
        est_hours_str = self.est_hours_entry.get().strip()
        if est_hours_str:
            try:
                float(est_hours_str)
            except ValueError:
                show_error("Input Error", "Estimated hours must be a valid number.")
                return False
        return True

    def _get_values(self):
        due_date = parse_date(self.due_date_entry.get())
        est_hours_str = self.est_hours_entry.get().strip()
        estimated_hours = float(est_hours_str) if est_hours_str else None

        return {
            "name": self.name_entry.get().strip(),
            "description": self.desc_textbox.get("1.0", "end-1c").strip(),
            "status": self.status_var.get(),
            "priority": self.priority_var.get(),
            "due_date": due_date,
            "estimated_hours": estimated_hours
        }


# --- Time Log Dialog ---
class TimeLogDialog(BaseDialog):
    def __init__(self, parent, title="Log Time"):
        super().__init__(parent, title)

    def _create_widgets(self):
        # Duration
        ctk.CTkLabel(self.main_frame, text="Duration (minutes):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.duration_entry = ctk.CTkEntry(self.main_frame, width=100)
        self.duration_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.duration_entry.focus_set() # Focus duration first

        # Log Date (Optional, defaults to now)
        ctk.CTkLabel(self.main_frame, text="Log Date:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.log_date_entry = DateEntry(self.main_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern=DATE_FORMAT.lower())
        self.log_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.log_date_entry.set_date(datetime.date.today()) # Default to today

        # Notes
        ctk.CTkLabel(self.main_frame, text="Notes:").grid(row=2, column=0, padx=5, pady=5, sticky="nw")
        self.notes_textbox = ctk.CTkTextbox(self.main_frame, height=60, width=250)
        self.notes_textbox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.main_frame.columnconfigure(1, weight=1)

    def _validate_input(self):
        duration_str = self.duration_entry.get().strip()
        if not duration_str:
            show_error("Input Error", "Duration cannot be empty.")
            return False
        try:
            duration = int(duration_str)
            if duration <= 0:
                show_error("Input Error", "Duration must be a positive number of minutes.")
                return False
        except ValueError:
            show_error("Input Error", "Duration must be a whole number (minutes).")
            return False

        # Validate date format implicitly handled by DateEntry
        log_date = parse_date(self.log_date_entry.get())
        if log_date is None and self.log_date_entry.get().strip(): # Check if entry has text but is invalid
             show_error("Input Error", f"Invalid date format. Please use {DATE_FORMAT}.")
             return False

        return True

    def _get_values(self):
        log_date = parse_date(self.log_date_entry.get())
        # Use today's date if entry is empty or invalid after validation passed (it shouldn't be invalid here)
        if log_date is None:
            log_date = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

        return {
            "duration_minutes": int(self.duration_entry.get().strip()),
            "log_date": log_date,
            "notes": self.notes_textbox.get("1.0", "end-1c").strip()
        }