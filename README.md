# 🤖 AI Robot – Autonomous Intelligent System

An autonomous AI-powered robot that uses computer vision, a large language model, and wireless motor control to explore, analyze, and navigate its environment in real time.

---

## 📸 Robot

![Robot](robot_img.jpeg)

---

## 🧠 System Architecture

| Part | Role |
|------|------|
| PC | Runs AI, vision, decision logic, report generation (main.py) |
| Raspberry Pi | Captures camera frames and streams them (raspi.py) |
| ESP32 | Controls motors, wheels, sensors, and LCD (esp.py) |
| Server | Local web interface for missions & reports (server.py) |

---

## 📦 Requirements

### PC
pip install -r pc_requirements.txt

### Raspberry Pi
pip install -r raspi_requirements.txt

### ESP32 (MicroPython)

Flash MicroPython:
esptool.py --chip esp32 erase_flash  
esptool.py --chip esp32 write_flash -z 0x1000 esp32-2024-xx-xx-v1.22.0.bin  

Upload to ESP32:
lcd.py  
lcd_i2c.py  
esp.py  

---

## 🚀 How to Use

1) Start Raspberry Pi camera stream  
python raspi.py  

2) Start local server  
python server.py  

3) Run AI brain  
python main.py  

4) Power the robot and ESP32  

The robot will:
- Receive camera frames  
- Analyze them with AI  
- Decide actions  
- Send movement commands  
- Display status on the LCD  
- Generate mission reports  

---

## 📄 Documentation

Robot-dExploration-IA-Specifications-Techniques.pdf  
AI-ROBOT-Un-Systeme-Autonome-Intelligent-1.pdf  

---

## 👤 Creator

Youssri Ben Hariz

---

## 📜 License

Free to use, modify, and build on.
