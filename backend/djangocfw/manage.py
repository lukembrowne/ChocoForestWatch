#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import debugpy
from time import sleep


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangocfw.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Try to attach debugger, but continue if it fails
    try:
        debugpy.listen(("0.0.0.0", 3000))
        print("⏳ VS Code debugger can now be attached, press F5 in VS Code ⏳")
        sleep(2)
    except Exception as e:
        print(f"⚠️  Unable to attach debugger: {str(e)} ⚠️")
        sleep(2)

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
