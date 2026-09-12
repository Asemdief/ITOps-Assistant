import os
import sys


def get_app_dir():
    """
    Return a writable directory next to the application.
    - When running as .exe (PyInstaller): folder containing the .exe
    - When running as script: project root (parent of modules/)
    """
    if getattr(sys, "frozen", False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as normal Python script
        modules_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(modules_dir)
