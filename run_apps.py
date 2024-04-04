import subprocess
import signal
import sys
import os

APPS = {
    "bot-api": ("poetry run python bot-api", {
        "PORT": "8000"
    }),
    "discord-gateway-relay": ("poetry run python relay-server", {
        "PORT": "8001"
    })
}

# ANSI escape codes for colors
GREEN_START = "\033[0;32m"
COLOR_END = "\033[0m"

processes: dict[str, subprocess.Popen] = {}


def terminate_processes(signal, frame):
    """Terminate all processes and exit with code 0"""

    for process in processes.values():
        process.terminate()

    sys.exit(0)


# Register a signal handler to capture termination signal (SIGINT)
signal.signal(signal.SIGINT, terminate_processes)

# Start all apps
for app_name, app_data in APPS.items():
    print(f"{GREEN_START}Starting {app_name}...{COLOR_END}")
    process = subprocess.Popen(
        app_data[0],
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
        universal_newlines=True,
        env=dict(os.environ, **(app_data[1] or {}))
    )
    processes[app_name] = process

# Continuously check and print errors if any
while processes:
    for app_name, process in dict(processes).items():
        return_code = process.poll()

        if return_code is not None:
            print(f"{GREEN_START}{app_name} completed successfully.{COLOR_END}")

            del processes[app_name]

# Ensure all processes are terminated before exiting
for process in processes.values():
    process.terminate()
