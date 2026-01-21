#!/usr/bin/env python3
"""
TEST BUTTON - Raspberry Pi Zero 2 W
===================================
Kết nối phần cứng:
  - Nút bấm chân 1 → Pin 11 (GPIO 17)
  - Nút bấm chân 2 → Pin 9 (GND)

Chạy: python3 test_mic.py
"""

import RPi.GPIO as GPIO
import time

# ============ CẤU HÌNH ============
BUTTON_PIN = 17  # Pin 11 trên header = GPIO 17

# ============ SETUP GPIO ============
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Pull-up resistor nội

# Biến đếm số lần nhấn
press_count = 0

# ============ CALLBACK KHI NHẤN NÚT ============
def button_pressed(channel):
    global press_count
    press_count += 1
    print(f"🔘 Nút được nhấn! (Lần thứ {press_count})")

# Đăng ký event - FALLING vì dùng pull-up (nhấn = LOW)
GPIO.add_event_detect(
    BUTTON_PIN,
    GPIO.FALLING,
    callback=button_pressed,
    bouncetime=300  # Chống rung 300ms
)

# ============ MAIN ============
print("=" * 40)
print("🔘 TEST BUTTON - Raspberry Pi Zero 2 W")
print("=" * 40)
print(f"📍 Button Pin: GPIO {BUTTON_PIN} (Pin 11)")
print("📍 GND: Pin 9")
print("-" * 40)
print("✅ Sẵn sàng! Nhấn nút để test...")
print("   Nhấn Ctrl+C để thoát")
print("=" * 40)

try:
    while True:
        time.sleep(0.1)  # Chờ event
        
except KeyboardInterrupt:
    print(f"\n👋 Thoát! Tổng số lần nhấn: {press_count}")
    
finally:
    GPIO.cleanup()
    print("✅ GPIO cleanup done!")
