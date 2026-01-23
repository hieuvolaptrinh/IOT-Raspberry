#!/usr/bin/env python3
"""
TEST MIC + BUTTON - Raspberry Pi Zero 2 W
=========================================
Nhấn nút lần 1: Bắt đầu ghi âm
Nhấn nút lần 2: Dừng ghi âm và lưu file

Kết nối phần cứng:
  - Nút bấm: Pin 11 (GPIO 17) + Pin 9 (GND)
  - Mic: Cắm vào cổng USB hoặc audio jack

Chạy: sudo python3 test_mic.py
"""

import RPi.GPIO as GPIO
import subprocess
import time
import os
from datetime import datetime

# ============ CẤU HÌNH ============
BUTTON_PIN = 17  # Pin 11 = GPIO 17
# Lưu file ghi âm cùng thư mục với script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDING_DIR = SCRIPT_DIR

# Audio settings
AUDIO_DEVICE = "plughw:0,0"  # USB PnP Sound Device (card 0)
# AUDIO_DEVICE = "plughw:1,0"  # USB mic thường là device 1 (chạy: arecord -l để xem)
SAMPLE_RATE = 44100
CHANNELS = 1

# ============ CLEANUP TRƯỚC ============
try:
    GPIO.cleanup()
except:
    pass

# ============ SETUP GPIO ============
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Tạo thư mục recordings nếu chưa có
os.makedirs(RECORDING_DIR, exist_ok=True)

# ============ BIẾN TRẠNG THÁI ============
is_recording = False
record_process = None
current_file = None
last_state = GPIO.HIGH

# ============ HÀM GHI ÂM ============
def start_recording():
    """Bắt đầu ghi âm với arecord"""
    global record_process, current_file, is_recording
    
    # Tạo tên file với timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_file = f"{RECORDING_DIR}/recording_{timestamp}.wav"
    
    print(f"🔴 BẮT ĐẦU GHI ÂM...")
    print(f"📁 File: {current_file}")
    
    # Chạy arecord trong background
    record_process = subprocess.Popen([
        'arecord',
        '-D', AUDIO_DEVICE,
        '-f', 'S16_LE',        # 16-bit signed little-endian
        '-r', str(SAMPLE_RATE),
        '-c', str(CHANNELS),
        '-t', 'wav',
        current_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    is_recording = True
    print("🎤 Đang ghi âm... (Nhấn nút để dừng)")

def stop_recording():
    """Dừng ghi âm"""
    global record_process, is_recording
    
    if record_process:
        record_process.terminate()
        record_process.wait()
        record_process = None
    
    is_recording = False
    
    print("⏹️  DỪNG GHI ÂM!")
    
    # Kiểm tra file đã lưu
    if current_file and os.path.exists(current_file):
        size = os.path.getsize(current_file)
        print(f"✅ Đã lưu: {current_file}")
        print(f"📊 Kích thước: {size / 1024:.1f} KB")
    else:
        print("❌ Lỗi: Không lưu được file!")

# ============ MAIN ============
print("=" * 50)
print("🎤 TEST MIC + BUTTON - Raspberry Pi Zero 2 W")
print("=" * 50)
print(f"📍 Button: GPIO {BUTTON_PIN} (Pin 11)")
print(f"� Recordings: {RECORDING_DIR}")
print("-" * 50)
print("✅ Sẵn sàng!")
print("   👉 Nhấn nút lần 1: Bắt đầu ghi âm")
print("   👉 Nhấn nút lần 2: Dừng và lưu")
print("   Nhấn Ctrl+C để thoát")
print("=" * 50)

try:
    while True:
        current_state = GPIO.input(BUTTON_PIN)
        
        # Phát hiện nhấn nút (HIGH → LOW)
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            if not is_recording:
                start_recording()
            else:
                stop_recording()
                print("-" * 50)
                print("✅ Sẵn sàng ghi tiếp! Nhấn nút...")
            
            time.sleep(0.3)  # Debounce
        
        last_state = current_state
        time.sleep(0.01)
        
except KeyboardInterrupt:
    print("\n👋 Đang thoát...")
    if is_recording:
        stop_recording()
    
finally:
    GPIO.cleanup()
    print("✅ GPIO cleanup done!")
