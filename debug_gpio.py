#!/usr/bin/env python3
"""
Script để debug và kiểm tra LCD ST7789
Chạy: python3 debug_gpio.py
"""

import RPi.GPIO as GPIO
import time
import spidev

print("=" * 50)
print("DEBUG LCD ST7789")
print("=" * 50)

# Định nghĩa các chân GPIO (BCM numbering)
DC_PIN = 24    # Pin 18
RST_PIN = 25   # Pin 22
BL_PIN = 18    # Pin 12

# === TEST 1: Kiểm tra GPIO ===
print("\n[TEST 1] Kiểm tra GPIO pins...")
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

try:
    GPIO.setup(DC_PIN, GPIO.OUT)
    GPIO.setup(RST_PIN, GPIO.OUT)
    GPIO.setup(BL_PIN, GPIO.OUT)
    print(f"  ✓ DC (GPIO {DC_PIN}) - OK")
    print(f"  ✓ RST (GPIO {RST_PIN}) - OK")
    print(f"  ✓ BL (GPIO {BL_PIN}) - OK")
except Exception as e:
    print(f"  ✗ Lỗi GPIO: {e}")

# === TEST 2: Kiểm tra Backlight ===
print("\n[TEST 2] Test Backlight...")
print("  Bật backlight...")
GPIO.output(BL_PIN, GPIO.HIGH)
time.sleep(1)
print("  Tắt backlight...")
GPIO.output(BL_PIN, GPIO.LOW)
time.sleep(1)
print("  Bật lại backlight...")
GPIO.output(BL_PIN, GPIO.HIGH)
print("  → Backlight có sáng/tắt không?")

# === TEST 3: Kiểm tra SPI ===
print("\n[TEST 3] Kiểm tra SPI...")
try:
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1000000  # 1MHz để test
    print("  ✓ SPI mở thành công!")
    print(f"  Mode: {spi.mode}")
    print(f"  Max Speed: {spi.max_speed_hz} Hz")
    spi.close()
except Exception as e:
    print(f"  ✗ Lỗi SPI: {e}")
    print("  → Chạy: sudo raspi-config → Interface Options → SPI → Enable")

# === TEST 4: Reset màn hình ===
print("\n[TEST 4] Reset màn hình...")
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.1)
GPIO.output(RST_PIN, GPIO.LOW)
time.sleep(0.1)
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.1)
print("  ✓ Đã gửi tín hiệu reset")

# === TEST 5: Gửi lệnh khởi tạo cơ bản ===
print("\n[TEST 5] Gửi lệnh khởi tạo ST7789...")
try:
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 10000000  # 10MHz
    spi.mode = 0
    
    def send_command(cmd):
        GPIO.output(DC_PIN, GPIO.LOW)
        spi.writebytes([cmd])
    
    def send_data(data):
        GPIO.output(DC_PIN, GPIO.HIGH)
        if isinstance(data, int):
            spi.writebytes([data])
        else:
            spi.writebytes(list(data))
    
    # Sleep Out
    send_command(0x11)
    time.sleep(0.12)
    
    # Display ON
    send_command(0x29)
    time.sleep(0.1)
    
    # Memory Access Control
    send_command(0x36)
    send_data(0x00)
    
    # Color Mode 16-bit
    send_command(0x3A)
    send_data(0x55)
    
    print("  ✓ Đã gửi lệnh khởi tạo")
    
    # Tô màu đỏ
    print("\n[TEST 6] Tô màu đỏ lên màn hình...")
    send_command(0x2A)  # Column
    send_data([0x00, 0x00, 0x00, 0xEF])
    send_command(0x2B)  # Row
    send_data([0x00, 0x00, 0x00, 0xEF])
    send_command(0x2C)  # Memory Write
    
    # Gửi pixel màu đỏ (RGB565: 0xF800)
    red_pixel = [0xF8, 0x00]  # Red in RGB565
    for _ in range(240):
        for _ in range(240):
            send_data(red_pixel)
    
    print("  ✓ Đã gửi dữ liệu màu đỏ")
    spi.close()
    
except Exception as e:
    print(f"  ✗ Lỗi: {e}")

print("\n" + "=" * 50)
print("KẾT QUẢ:")
print("- Nếu backlight không sáng → Kiểm tra chân BL hoặc nối BL vào 3.3V")
print("- Nếu màn hình trắng/đen → Sai chân DC/RST hoặc màn hình khác loại")
print("- Nếu hiện màu đỏ → LCD hoạt động OK!")
print("=" * 50)

GPIO.cleanup()
