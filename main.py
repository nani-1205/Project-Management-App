# project_tracker/main.py
from ui.app_window import AppWindow

if __name__ == "__main__":
    app = AppWindow()
    # Only run if the window initialization didn't fail due to DB connection
    if app.winfo_exists():
        app.run()