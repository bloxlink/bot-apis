import subprocess
import signal

APPS = {
    "roblox-info-server": "python3.10 src/main.py",
    "bot-api": "python3.10 src/main.py",
    "discord-gateway-relay": "python3.10 src/main.py"
}

# ANSI escape codes for colors
GREEN_START = "\033[0;32m"
COLOR_END = "\033[0m"

processes = []


def terminate_processes(signal, frame):
    for process in processes:
        process.terminate()
    exit(0)


# Register a signal handler to capture termination signal (SIGINT)
signal.signal(signal.SIGINT, terminate_processes)

# Start all apps
for app_name, app_run_command in APPS.items():
    print(f"{GREEN_START}Starting {app_name}...{COLOR_END}")
    process = subprocess.Popen(
        f"cd src/apps/{app_name}; {app_run_command}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    processes.append(process)

# Continuously check and print errors if any
while processes:
    for process in processes:
        retcode = process.poll()
        if retcode is not None:
            stdout, stderr = process.communicate()
            if retcode != 0:
                print(f"Error occurred in {app_name}:")
                print("Standard Output:")
                print(stdout)
                print("Standard Error:")
                print(stderr)
            else:
                print(f"{app_name} completed successfully.")
            processes.remove(process)

# Ensure all processes are terminated before exiting
for process in processes:
    process.terminate()
