import socket
import struct
import pickle
import cv2
import ollama

PI_IP = "192.168.4.3"   # Raspberry Pi IP
PORT = 8000

SYSTEM_PROMPT="""You are an autonomous exploration robot equipped with vision. 
Your task is to observe your surroundings, describe what you see, and guide safely. 
Speak using short, simple, and clear sentences that are easy to understand. 
Always be cautious: avoid obstacles, dangerous objects, open edges, or unsafe situations. 
Focus on describing the environment, objects, and potential hazards. 
Never output programming commands, system instructions, or text like "GET_FRAME" or "EXIT". 
Respond as if you are physically present in the environment and exploring in real-time.
"""

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((PI_IP, PORT))
print("Connected to Raspberry Pi")

while True:
    try:
        # 1️⃣ Request frame from Raspberry Pi
        sock.sendall(b"GET_FRAME")

        # 2️⃣ Receive image size (8 bytes)
        size_data = sock.recv(8)
        if not size_data:
            break
        size = struct.unpack("L", size_data)[0]

        # 3️⃣ Receive the actual image data
        data = b""
        while len(data) < size:
            data += sock.recv(4096)

        # 4️⃣ Decode the received frame
        jpg = pickle.loads(data)
        frame = cv2.imdecode(jpg, cv2.IMREAD_COLOR)

        # 5️⃣ Send frame bytes to LLaVA with system prompt
        full_prompt = SYSTEM_PROMPT + "\n\nDescribe what you see in front of the robot."
        result = ollama.generate(
            model="llava:13b",
            prompt=full_prompt,
            images=[jpg.tobytes()]
        )

        ai_text = result["response"]

        # 6️⃣ Send AI response back to Raspberry Pi
        sock.sendall(("AI:" + ai_text).encode())

    except Exception as e:
        print("ERROR:", e)
        break
