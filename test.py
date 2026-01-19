#!/usr/bin/env python3
"""
FULL DEBUG for ST7789 LCD on Raspberry Pi
LCD đã hoạt động với Arduino, cần debug kết nối với Pi
"""
import os
import time

print("=" * 60)
print("  ST7789 FULL DEBUG - Raspberry Pi")
print("=" * 60)

# ==================== CHECK 1: SPI ENABLED ====================
print("\n[1] Kiểm tra SPI...")
if os.path.exists("/dev/spidev0.0"):
    print("    ✓ SPI0.0 đã bật")
else:
    print("    ✗ SPI CHƯA BẬT!")
    print("    → Chạy: sudo raspi-config nonint do_spi 0")
    print("    → Sau đó reboot")
    exit(1)

# ==================== CHECK 2: IMPORTS ====================
print("\n[2] Kiểm tra thư viện...")
try:
    import RPi.GPIO as GPIO
    print("    ✓ RPi.GPIO OK")
except ImportError as e:
    print(f"    ✗ RPi.GPIO lỗi: {e}")
    exit(1)

try:
    import spidev
    print("    ✓ spidev OK")
except ImportError as e:
    print(f"    ✗ spidev lỗi: {e}")
    exit(1)

# ==================== GPIO SETUP ====================
DC = 25
RST = 27  
BL = 18

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC, GPIO.OUT)
GPIO.setup(RST, GPIO.OUT)
GPIO.setup(BL, GPIO.OUT)

# ==================== CHECK 3: BACKLIGHT ====================
print("\n[3] Test Backlight...")
GPIO.output(BL, GPIO.HIGH)
print("    Backlight GPIO 18 = HIGH")
print("    → Màn hình có sáng không? (kiểm tra bằng mắt)")

# ==================== CHECK 4: SPI COMMUNICATION ====================
print("\n[4] Khởi tạo SPI...")
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 10000000  # Giảm xuống 10MHz để ổn định
spi.mode = 0b00  # Mode 0: CPOL=0, CPHA=0

print(f"    SPI Speed: {spi.max_speed_hz} Hz")
print(f"    SPI Mode: {spi.mode}")

# ==================== HELPER FUNCTIONS ====================
def command(cmd):
    GPIO.output(DC, GPIO.LOW)
    spi.xfer2([cmd])

def data(val):
    GPIO.output(DC, GPIO.HIGH)
    if isinstance(val, list):
        spi.xfer2(val)
    else:
        spi.xfer2([val])

def reset():
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(RST, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(0.15)

# ==================== CHECK 5: RESET ====================
print("\n[5] Hardware Reset...")
reset()
print("    ✓ Reset hoàn tất")

# ==================== CHECK 6: INIT SEQUENCE ====================
print("\n[6] Khởi tạo ST7789 (init sequence)...")

# Sleep Out
command(0x11)
time.sleep(0.12)
print("    → Sleep Out (0x11)")

# Memory Data Access Control - THỬ NHIỀU GIÁ TRỊ
# 0x00: Normal
# 0x70: BGR + Mirror X + Mirror Y  
# 0xC0: Mirror Y
command(0x36)
data(0x00)  # Thử 0x00, 0x70, 0xC0
print("    → MADCTL (0x36) = 0x00")

# Interface Pixel Format - 16bit RGB565
command(0x3A)
data(0x55)
print("    → Pixel Format (0x3A) = 0x55 (16bit)")

# Display Inversion ON - một số LCD cần, một số không
command(0x21)
print("    → Display Inversion ON (0x21)")

# Display ON
command(0x29)
time.sleep(0.1)
print("    → Display ON (0x29)")

print("    ✓ Init hoàn tất")

# ==================== CHECK 7: FILL COLOR ====================
print("\n[7] Fill màn hình màu ĐỎ...")

# Set Column Address (0-239)
command(0x2A)
data([0x00, 0x00, 0x00, 0xEF])

# Set Row Address (0-239)
command(0x2B)
data([0x00, 0x00, 0x00, 0xEF])

# Write Memory
command(0x2C)

# Send RED pixels (RGB565: 0xF800)
GPIO.output(DC, GPIO.HIGH)
red_high = 0xF8
red_low = 0x00
pixel_data = [red_high, red_low] * 512  # 512 pixels mỗi lần

total_pixels = 240 * 240
sent = 0
while sent < total_pixels:
    batch = min(512, total_pixels - sent)
    spi.xfer2([red_high, red_low] * batch)
    sent += batch

print("    ✓ Đã gửi 240x240 pixels màu đỏ")

# ==================== SUMMARY ====================
print("\n" + "=" * 60)
print("  DEBUG HOÀN TẤT")
print("=" * 60)
print("""
Kết quả mong đợi: Màn hình hiển thị màu ĐỎ

NẾU KHÔNG THẤY GÌ, kiểm tra:
1. Dây SCL (GPIO 11 / Pin 23) - đảm bảo kết nối chắc
2. Dây SDA (GPIO 10 / Pin 19) - đảm bảo kết nối chắc
3. Dây DC  (GPIO 25 / Pin 22) - RẤT QUAN TRỌNG!
4. Dây RST (GPIO 27 / Pin 13) - thử nối trực tiếp vào 3.3V

THỬ THÊM:
- Hoán đổi SCL và SDA (một số LCD ghi nhầm)
- Giảm SPI speed xuống 1MHz
- Kiểm tra nguồn 3.3V đủ mạnh không

Nhấn Ctrl+C để thoát...
""")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nĐang cleanup...")
    spi.close()
    GPIO.cleanup()
    print("Đã dừng.")