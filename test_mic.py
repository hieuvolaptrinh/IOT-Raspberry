#!/usr/bin/env python3
"""
TEST BUTTON - Raspberry Pi Zero 2 W
===================================
Kết nối phần cứng:
  - Nút bấm chân 1 → Pin 11 (GPIO 17)
  - Nút bấm chân 2 → Pin 9 (GND)

Chạy: sudo python3 test_mic.py
"""

import RPi.GPIO as GPIO
import time

# ============ CẤU HÌNH ============
BUTTON_PIN = 17  # Pin 11 trên header = GPIO 17

# ============ CLEANUP TRƯỚC ============
# Giải phóng GPIO nếu đang bị chiếm
try:
    GPIO.cleanup()
except:
    pass

# ============ SETUP GPIO ============
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("=" * 40)
print("🔘 TEST BUTTON - Raspberry Pi Zero 2 W")
print("=" * 40)
print(f"📍 Button Pin: GPIO {BUTTON_PIN} (Pin 11)")
print("📍 GND: Pin 9")
print("-" * 40)
print("✅ Sẵn sàng! Nhấn nút để test...")
print("   Nhấn Ctrl+C để thoát")
print("=" * 40)

# Biến đếm và trạng thái
press_count = 0
last_state = GPIO.HIGH  # Pull-up nên mặc định là HIGH

try:
    while True:
        current_state = GPIO.input(BUTTON_PIN)
        
        # Phát hiện nhấn nút (HIGH → LOW)
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            press_count += 1
            print(f"🔘 Nút được nhấn! (Lần thứ {press_count})")
            time.sleep(0.2)  # Debounce - chờ hết rung
        
        last_state = current_state
        time.sleep(0.01)  # Polling 100Hz
        
except KeyboardInterrupt:
    print(f"\n👋 Thoát! Tổng số lần nhấn: {press_count}")
    
finally:
    GPIO.cleanup()
    print("✅ GPIO cleanup done!")
