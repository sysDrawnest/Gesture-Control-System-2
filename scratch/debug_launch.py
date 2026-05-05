import os
import subprocess
import sys

client_name = "presentation_game"
project_root = r"c:\Users\PRATINGYA\Documents\Code\project\Gesture Control System"
client_dir = os.path.join(project_root, "client")
script_name = f"{client_name}.py"
games_dir = os.path.join(client_dir, "games")
game_script_path = os.path.join(games_dir, script_name)

print(f"Checking: {game_script_path}")
if os.path.exists(game_script_path):
    print("Found in games_dir")
    client_dir = games_dir
    script_path = game_script_path
else:
    print("Not found in games_dir")
    script_path = os.path.join(client_dir, script_name)

print(f"Running: {sys.executable} {script_name}")
print(f"In CWD: {client_dir}")

try:
    # We won't use CREATE_NEW_CONSOLE here so we can see output in the scratch script
    process = subprocess.Popen(
        [sys.executable, script_name],
        cwd=client_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    # Give it 2 seconds to see if it crashes
    try:
        stdout, stderr = process.communicate(timeout=3)
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
    except subprocess.TimeoutExpired:
        print("Process started and is still running (Success)")
        process.terminate()
except Exception as e:
    print("Error:", e)
