import socket
import cv2
import struct
import pickle
import time
import pyttsx3
import subprocess
import pygame
import threading
import math

# ---------------- CONFIG ----------------
HOST = "0.0.0.0"
PORT = 8000
CAM_INDEX = "/dev/video0"
JPEG_QUALITY = 100

ESP_SSID = "AI_ROBOT"          # ESP32 AP name
ESP_PASSWORD = "12345678"      # Replace with your ESP password

# ---------------- AUTO CONNECT TO ESP AP ----------------
def connect_to_esp():
    connected = False
    while not connected:
        try:
            # Check current connection
            output = subprocess.check_output("nmcli -t -f ACTIVE,SSID dev wifi", shell=True).decode()
            for line in output.splitlines():
                active, ssid = line.split(":")
                if active == "yes" and ssid == ESP_SSID:
                    print(f"Already connected to {ESP_SSID}")
                    connected = True
                    break

            if not connected:
                print(f"Connecting to {ESP_SSID}...")
                subprocess.run(f"nmcli dev wifi connect '{ESP_SSID}' password '{ESP_PASSWORD}'", shell=True)
                time.sleep(5)  # give it some time to connect

        except Exception as e:
            print("WiFi connection failed:", e)
            time.sleep(3)

connect_to_esp()  # wait for WiFi before starting

# ---------------- BLUETOOTH TTS ----------------
def get_bluetooth_speaker_sink():
    try:
        sinks = subprocess.check_output("pactl list short sinks", shell=True).decode()
        for line in sinks.splitlines():
            if "bluez_sink" in line:
                sink_name = line.split()[1]
                subprocess.run(f"pacmd set-default-sink {sink_name}", shell=True)
                print(f"TTS routed to Bluetooth speaker: {sink_name}")
                return sink_name
    except Exception as e:
        print("Bluetooth speaker detection failed:", e)
    return None

get_bluetooth_speaker_sink()

# ---------------- TTS ----------------
engine = pyttsx3.init()
engine.setProperty('rate', 145)
engine.setProperty('volume', 1.0)
speaking_flag = threading.Event()

def tts_speak(text):
    speaking_flag.set()
    engine.say(text)
    engine.runAndWait()
    speaking_flag.clear()

# ---------------- CAMERA ----------------
cam = cv2.VideoCapture(CAM_INDEX)
if not cam.isOpened():
    print(f"No camera found at {CAM_INDEX}")
    exit()

# ---------------- PYGAME UI ----------------
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Cute AI Robot UI")
clock = pygame.time.Clock()

ui_state = "booting"

# Face layout
eye_radius = 50
eye_offset_x = 120
eye_offset_y = 40
center_x = screen.get_width() // 2
center_y = screen.get_height() // 2

mouth_width = 100
mouth_height = 14

# Animations
blink_timer = 0
blink_interval = 3.5
blink_duration = 0.18
blink_progress = 0
mouth_anim_progress = 0

boot_progress = 0.0
boot_jiggle = 0.0
boot_done = False

# ---------------- BOOT SEQUENCE ----------------
def startup_sequence():
    global ui_state, boot_done
    time.sleep(0.6)
    tts_speak("Power on. Hello everyone, please enjoy watching me.")
    boot_done = True
    time.sleep(1.2)
    ui_state = "idle"

threading.Thread(target=startup_sequence, daemon=True).start()

# ---------------- DRAW FACE ----------------
def draw_robot_face(dt):
    global blink_timer, blink_progress, mouth_anim_progress
    global boot_progress, boot_jiggle

    screen.fill((18, 18, 40))

    if ui_state == "booting":
        boot_progress = min(1.0, boot_progress + dt * 0.25)   # slower open
        boot_jiggle += dt * 4                                 # softer movement
        jiggle_x = math.sin(boot_jiggle) * 4
        jiggle_y = math.cos(boot_jiggle * 0.8) * 3
    else:
        jiggle_x = 0
        jiggle_y = 0

    blink_timer += dt
    if blink_timer >= blink_interval:
        blink_progress += dt
        if blink_progress >= blink_duration:
            blink_progress = 0
            blink_timer = 0

    if ui_state == "talking":
        eye_color = (60, 255, 80)
        mouth_anim_progress += dt * 8
    else:
        eye_color = (80, 160, 255)
        mouth_anim_progress += dt * 2

    if ui_state == "booting":
        open_factor = boot_progress
    else:
        open_factor = 1 - 0.5 * math.sin((blink_progress / blink_duration) * math.pi) if blink_progress else 1

    # Eyes
    for ex in (-eye_offset_x, eye_offset_x):
        eye_h = eye_radius * open_factor
        pygame.draw.ellipse(screen, eye_color, (
            center_x + ex - eye_radius + jiggle_x,
            center_y - eye_offset_y - eye_h//2 + jiggle_y,
            eye_radius * 2,
            eye_h * 2
        ))

    # Mouth
    if ui_state == "talking":
        mouth_h = mouth_height + math.sin(mouth_anim_progress) * 10
    elif ui_state == "booting":
        mouth_h = 4
    else:
        mouth_h = mouth_height + math.sin(mouth_anim_progress) * 3

    mouth_rect = pygame.Rect(
        center_x - mouth_width//2 + jiggle_x,
        center_y + eye_offset_y + 12 + jiggle_y,
        mouth_width,
        int(mouth_h)
    )

    pygame.draw.ellipse(screen, eye_color, mouth_rect)

    pygame.display.flip()

# ---------------- SOCKET ----------------
def socket_thread():
    global ui_state
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    print("Waiting for PC...")
    conn, addr = server.accept()
    print("PC connected:", addr)

    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                print("PC disconnected.")
                ui_state = "talking"
                tts_speak("Goodbye everyone, I hope you enjoyed the exploration.")
                ui_state = "idle"
                break

            if data.startswith("AI:"):
                ui_state = "talking"
                tts_speak(data[3:])
                ui_state = "idle"

            elif data == "GET_FRAME":
                while speaking_flag.is_set():
                    time.sleep(0.05)

                cam.grab()
                ret, frame = cam.read()
                if not ret:
                    continue

                frame = cv2.resize(frame, (320, 240))
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                payload = pickle.dumps(buffer)
                conn.sendall(struct.pack("L", len(payload)) + payload)

        except Exception as e:
            print("ERROR:", e)
            ui_state = "talking"
            tts_speak("Goodbye everyone, I hope you enjoyed the exploration.")
            ui_state = "idle"
            time.sleep(1)
            break

threading.Thread(target=socket_thread, daemon=True).start()

# ---------------- MAIN LOOP ----------------
running = True
last = time.time()

while running:
    now = time.time()
    dt = now - last
    last = now

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    draw_robot_face(dt)
    clock.tick(30)

pygame.quit()
