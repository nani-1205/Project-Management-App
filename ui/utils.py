# project_tracker/ui/utils.py
import datetime
from config import DATE_FORMAT, DATETIME_FORMAT
from tkinter import messagebox

def format_date(dt):
    """Formats a datetime object into a string, handles None."""
    if isinstance(dt, datetime.datetime):
        return dt.strftime(DATE_FORMAT)
    return ""

def format_datetime(dt):
    """Formats a datetime object to include time, handles None."""
    if isinstance(dt, datetime.datetime):
        # Try to convert timezone aware to local time if needed,
        # but for simplicity assume consistent timezone or UTC display
        return dt.strftime(DATETIME_FORMAT)
    return ""

def parse_date(date_str):
    """Parses a date string into a datetime object, handles errors."""
    if not date_str:
        return None
    try:
        # Use combine to set time to midnight
        d = datetime.datetime.strptime(date_str, DATE_FORMAT).date()
        return datetime.datetime.combine(d, datetime.time.min) # Set time to 00:00:00
    except ValueError:
        return None # Indicate parsing failure

def format_duration(total_minutes):
    """Formats total minutes into Hh Mm format."""
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

def show_error(title, message):
    """Displays an error message box."""
    messagebox.showerror(title, message)

def show_info(title, message):
    """Displays an informational message box."""
    messagebox.showinfo(title, message)

def ask_yes_no(title, message):
    """Asks a Yes/No question and returns True for Yes, False for No."""
    return messagebox.askyesno(title, message)