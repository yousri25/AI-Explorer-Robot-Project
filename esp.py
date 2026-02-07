import network
import socket
import time
from machine import Pin, PWM, time_pulse_us, I2C
import _thread

# ================= LCD =================
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

from lcd_api import LcdApi
from i2c_lcd import I2cLcd

LCD_ADDR = 0x27
LCD_ROWS = 2
LCD_COLS = 16

time.sleep(1.5)   # <-- let LCD power up

while True:
    try:
        lcd = I2cLcd(i2c, LCD_ADDR, LCD_ROWS, LCD_COLS)
        break
    except:
        print("Waiting for LCD...")
        time.sleep(0.5)

lcd.clear()
lcd.putstr("AI ROBOT\nIDLE")

def lcd_show(cmd):
    lcd.clear()
    lcd.putstr("CMD:\n" + cmd)

# ================= WIFI AP =================
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="AI_ROBOT", password="12345678")
print("ESP32 AP IP:", ap.ifconfig())

# ================= MOTOR SETUP =================
m1a = Pin(27, Pin.OUT)
m1b = Pin(26, Pin.OUT)
m2a = Pin(25, Pin.OUT)
m2b = Pin(33, Pin.OUT)

ena = Pin(14, Pin.OUT)
enb = Pin(12, Pin.OUT)
ena.value(1)
enb.value(1)

MOVE_TIME = 3
TURN_TIME = 1

# ================= LED & BUZZER =================
led = Pin(2, Pin.OUT)
buzzer = PWM(Pin(4))
buzzer.freq(1000)
buzzer.duty_u16(0)

# ================= ULTRASONIC =================
trig = Pin(5, Pin.OUT)
echo = Pin(18, Pin.IN)

def get_distance_cm():
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    duration = time_pulse_us(echo, 1, 30000)
    if duration < 0:
        return None
    return (duration / 2) / 29.1

# ================= EMERGENCY =================
emergency = False
last_escape_time = 0

# ================= MOTOR =================
def stop_motors():
    m1a.value(0)
    m1b.value(0)
    m2a.value(0)
    m2b.value(0)

def forward():
    m1a.value(1); m1b.value(0)
    m2a.value(1); m2b.value(0)
    time.sleep(MOVE_TIME)
    stop_motors()

def backward():
    m1a.value(0); m1b.value(1)
    m2a.value(0); m2b.value(1)
    time.sleep(MOVE_TIME)
    stop_motors()

def left():
    m1a.value(0); m1b.value(1)
    m2a.value(1); m2b.value(0)
    time.sleep(TURN_TIME)
    stop_motors()

def right():
    m1a.value(1); m1b.value(0)
    m2a.value(0); m2b.value(1)
    time.sleep(TURN_TIME)
    stop_motors()

# ================= HEARTBEAT =================
def heartbeat():
    while True:
        led.on()
        time.sleep(0.5)
        led.off()
        time.sleep(0.5)

_thread.start_new_thread(heartbeat, ())

# ================= ESCAPE ROUTINE =================
def escape_routine():
    global emergency

    print("!!! OBSTACLE ESCAPE !!!")
    stop_motors()
    lcd_show("ESCAPE")

    m1a.value(0); m1b.value(1)
    m2a.value(0); m2b.value(1)
    time.sleep(0.5)
    stop_motors()

    m1a.value(1); m1b.value(0)
    m2a.value(0); m2b.value(1)
    time.sleep(2)
    stop_motors()

    emergency = False
    lcd_show("IDLE")

# ================= ULTRASONIC LOOP =================
def ultrasonic_loop():
    global emergency, last_escape_time

    while True:
        dist = get_distance_cm()

        if dist is not None and dist < 15:
            buzzer.duty_u16(30000)
        else:
            buzzer.duty_u16(0)

        if dist is not None and dist < 15 and not emergency:
            if time.ticks_ms() - last_escape_time > 3000:
                emergency = True
                last_escape_time = time.ticks_ms()
                _thread.start_new_thread(escape_routine, ())

        time.sleep(0.05)

_thread.start_new_thread(ultrasonic_loop, ())

# ================= TCP SERVER =================
server = socket.socket()
server.bind(("", 9000))
server.listen(1)
server.settimeout(1)
print("Waiting for PC...")

conn = None
addr = None

while conn is None:
    try:
        conn, addr = server.accept()
    except:
        time.sleep(0.1)

print("PC connected:", addr)
conn.settimeout(0.1)

lcd_show("CONNECTED")

# ================= MAIN LOOP =================
while True:
    try:
        if conn:
            try:
                data = conn.recv(64)
                if data:
                    cmd = data.decode().strip().upper()
                    print("CMD:", cmd)
                    lcd_show(cmd)

                    if not emergency:
                        if cmd == "FORWARD":
                            forward()
                        elif cmd == "BACKWARD":
                            backward()
                        elif cmd == "LEFT":
                            left()
                        elif cmd == "RIGHT":
                            right()
                        elif cmd == "STOP":
                            stop_motors()
                            lcd_show("IDLE")
            except OSError:
                pass
    except Exception as e:
        print("Error:", e)
    time.sleep(0.05)
