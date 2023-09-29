import subprocess
import signal

APPS = {
    "roblox-info-server": "python3.10 src/main.py",
    "bot-api": "python3.10 src/main.py",
    "discord-gateway-relay": "python3.10 src/main.py"
}

processes = []


def terminate_processes(signal, frame):
    for process in processes:
        process.terminate()
    exit(0)


# Register a signal handler to capture termination signal (SIGINT)
signal.signal(signal.SIGINT, terminate_processes)

# Start all apps
for app_name, app_run_command in APPS.items():
    process = subprocess.Popen(
        f"cd src/apps/{app_name}; {app_run_command}", shell=True)
    processes.append(process)

for process in processes:
    process.wait()
