import subprocess
import signal
import sys

APPS = {
    "roblox-info-server": "cd src/apps/roblox-info-server; python3.10 src/main.py",
    "bot-api": "poetry run python bot-api",
    "discord-gateway-relay": "poetry run python relay-server"
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
for app_name, app_run_command in APPS.items():
    print(f"{GREEN_START}Starting {app_name}...{COLOR_END}")
    process = subprocess.Popen(
        app_run_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    processes[app_name] = process

# Continuously check and print errors if any
while processes:
    for app_name, process in dict(processes).items():
        return_code = process.poll()

        if return_code is not None:
            stdout, stderr = process.communicate()

            if return_code != 0:
                print(f"Error occurred in {app_name}:")

                if stdout:
                    print(f"Output: {stdout}")

                if stderr:
                    print(stderr)
            else:
                print(f"{app_name} completed successfully.")

            del processes[app_name]

# Ensure all processes are terminated before exiting
for process in processes.values():
    process.terminate()
