import subprocess

APPS = {
    "roblox-info-server": "python3.10 src/main.py",
    "bot-api": "python3.10 src/main.py",
    "discord-gateway-relay": "python3.10 src/main.py"
}

processes = []

for app_name, app_run_command in APPS.items():
    process = subprocess.Popen(f"cd src/apps/{app_name}; {app_run_command}", shell=True)
    processes.append(process)

for process in processes:
    process.wait()
