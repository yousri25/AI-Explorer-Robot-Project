import socket
import struct
import pickle
import cv2
import ollama
import time
import os
from datetime import datetime
import threading
import signal
import sys

# ================== IP CONFIG ==================
PI_IP = "192.168.4.4"
PI_PORT = 8000

ESP_IP = "192.168.4.1"
ESP_PORT = 9000

# ================== SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
You are an autonomous mobile robot with a camera.
Your mission is to move forward and explore safely.

You must ALWAYS respond using this exact format:

[THOUGHT]
Describe what you see using short, clear sentences.

[ACTION]
Choose exactly ONE:
FORWARD
BACKWARD
LEFT
RIGHT
STOP

Behavior rules:
- Your main goal is to keep moving forward.
- If the path ahead is clear → choose FORWARD.
- If an obstacle is in front → choose LEFT or RIGHT to go around it.
- If there is danger, a cliff, or no safe path → choose BACKWARD or STOP.
- Only choose STOP if no safe movement is possible.
- Never explain your decision.
- Never add anything outside this format.
- Stay focused. Stay active. Keep moving.
"""

# ================== EXPLORATION SETUP ==================
mission_id = datetime.now().strftime("mission_%Y-%m-%d_%H-%M")
BASE_DIR = f"explorations/{mission_id}"
FRAMES_DIR = f"{BASE_DIR}/frames"
os.makedirs(FRAMES_DIR, exist_ok=True)

log = []
stop_flag = False

REPORT_PATH = f"{BASE_DIR}/report.html"

# ================== REPORT SYSTEM (UPDATED UI) ==================
def write_report(final_text=None):
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AI Exploration Report</title>
<style>
* {{
    box-sizing: border-box;
    font-family: "Segoe UI", Arial, sans-serif;
}}

body {{
    margin: 0;
    background: #f4f7fb;
    color: #1a1a1a;
}}

header {{
    background: white;
    border-bottom: 3px solid #1e90ff;
    display: flex;
    align-items: center;
    padding: 15px 30px;
}}

header img {{
    height: 50px;
    margin-right: 15px;
}}

header h1 {{
    color: #1e90ff;
    margin: 0;
}}

.container {{
    width: 90%;
    max-width: 1100px;
    margin: 30px auto;
}}

.card {{
    background: white;
    border-left: 5px solid #1e90ff;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 20px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    display: flex;
    gap: 15px;
    align-items: center;
}}

.card img {{
    width: 220px;
    border-radius: 8px;
}}

.final {{
    background: #1e90ff;
    color: white;
    padding: 25px;
    border-radius: 12px;
    margin-top: 40px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}}
</style>
</head>
<body>

<header>
    <img src="../logo.jpg">
    <h1>AI Exploration Report</h1>
</header>

<div class="container">
    <p><b>Mission ID:</b> {mission_id}</p>
"""

    for item in log:
        html += f"""
        <div class="card">
            <img src="frames/{item['image']}">
            <p>{item['thought']}</p>
        </div>
        """

    if final_text:
        html += f"""
        <div class="final">
            <h2>Final Reflection</h2>
            <p>{final_text}</p>
        </div>
        """

    html += """
</div>
</body>
</html>
"""

    with open(REPORT_PATH, "w") as f:
        f.write(html)

# ================== CTRL+C HANDLER ==================
def handle_exit(sig, frame):
    print("\nStopping exploration... Generating final reflection...\n")

    if log:
        summary_prompt = "You explored a place with these observations:\n"
        for item in log:
            summary_prompt += f"- {item['thought']}\n"
        summary_prompt += "\nNow describe what this place is and how you felt during the exploration."

        final_reflection = ollama.generate(
            model="llava:13b",
            prompt=summary_prompt
        )["response"]
    else:
        final_reflection = "No observations were collected."

    write_report(final_reflection)
    print("Final report saved to:", REPORT_PATH)
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

# ================== CONNECT TO RASPI ==================
raspi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
raspi.connect((PI_IP, PI_PORT))
print("Connected to Raspberry Pi")

# ================== CONNECT TO ESP ==================
esp = socket.socket()
while True:
    try:
        esp.connect((ESP_IP, ESP_PORT))
        print("Connected to ESP32")
        break
    except:
        print("Retrying ESP...")
        time.sleep(2)

# ================== MAIN LOOP ==================
frame_count = 0

while True:
    try:
        raspi.sendall(b"GET_FRAME")

        size_data = raspi.recv(8)
        size = struct.unpack("L", size_data)[0]

        data = b""
        while len(data) < size:
            data += raspi.recv(4096)

        jpg = pickle.loads(data)
        frame = cv2.imdecode(jpg, cv2.IMREAD_COLOR)

        result = ollama.generate(
            model="llava:13b",
            prompt=SYSTEM_PROMPT,
            images=[jpg.tobytes()]
        )

        response = result["response"]
        print("\nAI RESPONSE:\n", response)

        thought = ""
        action = "STOP"

        if "[THOUGHT]" in response and "[ACTION]" in response:
            thought = response.split("[THOUGHT]")[1].split("[ACTION]")[0].strip()
            action = response.split("[ACTION]")[1].strip().upper()

        if action not in ["FORWARD", "BACKWARD", "LEFT", "RIGHT", "STOP"]:
            action = "STOP"

        esp.sendall(action.encode())
        print("Sent to ESP:", action)

        raspi.sendall(("AI:" + thought).encode())

        # ========== SAVE FRAME + LOG ==========
        frame_count += 1
        fname = f"frame_{frame_count:03}.jpg"
        fpath = f"{FRAMES_DIR}/{fname}"
        cv2.imwrite(fpath, frame)

        log.append({"image": fname, "thought": thought})

        # 🔥 LIVE REPORT UPDATE
        write_report()

    except Exception as e:
        print("ERROR:", e)
        break
