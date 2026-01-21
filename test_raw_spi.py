#!/usr/bin/env python3
"""
RAW SPI TEST - Chẩn đoán trực tiếp ST7789
Bypass tất cả thư viện, gửi command trực tiếp qua SPI
"""
import spidev
import RPi.GPIO as GPIO
import time

# ============ CẤU HÌNH PIN ============
# DC_PIN = 25      # Data/Command
# RST_PIN = 24     # Reset
BL_PIN = 18      # Backlight

# Nếu config trên không đúng, thử đổi:
DC_PIN = 24
RST_PIN = 25

print("=" * 55)
print(" RAW SPI DIAGNOSTIC - ST7789 1.54\"")
print("=" * 55)
print(f"\nCấu hình hiện tại:")
print(f"  DC  = GPIO{DC_PIN}")
print(f"  RST = GPIO{RST_PIN}")
print(f"  BL  = GPIO{BL_PIN}")

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)

# Bật backlight
GPIO.output(BL_PIN, GPIO.HIGH)
print("\n[1] Backlight: ON")

# Setup SPI
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 40000000
spi.mode = 0
print("[2] SPI: Initialized (40MHz, Mode 0)")

def send_cmd(cmd):
    """Gửi command"""
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.xfer2([cmd])

def send_data(data):
    """Gửi data"""
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(data, int):
        spi.xfer2([data])
    else:
        # Gửi từng chunk
        data = list(data)
        for i in range(0, len(data), 4096):
            spi.xfer2(data[i:i+4096])

def reset():
    """Hardware reset"""
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.01)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.15)

print("[3] Hardware Reset...")
reset()

# ============ KHỞI TẠO ST7789 ============
print("[4] Initializing ST7789...")

# Software Reset
send_cmd(0x01)
time.sleep(0.15)

# Sleep Out
send_cmd(0x11)
time.sleep(0.12)

# Memory Data Access Control (MADCTL)
# Thử các giá trị khác nhau nếu màu bị sai
send_cmd(0x36)
send_data(0x00)  # Thử: 0x00, 0x70, 0xC0, 0x08

# Interface Pixel Format - 16bit RGB565
send_cmd(0x3A)
send_data(0x55)

# Porch Setting
send_cmd(0xB2)
send_data([0x0C, 0x0C, 0x00, 0x33, 0x33])

# Gate Control
send_cmd(0xB7)
send_data(0x35)

# VCOM Setting
send_cmd(0xBB)
send_data(0x28)

# LCM Control
send_cmd(0xC0)
send_data(0x0C)

# VDV and VRH Command Enable
send_cmd(0xC2)
send_data([0x01, 0xFF])

# VRH Set
send_cmd(0xC3)
send_data(0x10)

# VDV Set
send_cmd(0xC4)
send_data(0x20)

# Frame Rate
send_cmd(0xC6)
send_data(0x0F)

# Power Control 1
send_cmd(0xD0)
send_data([0xA4, 0xA1])

# Positive Voltage Gamma
send_cmd(0xE0)
send_data([0xD0, 0x00, 0x02, 0x07, 0x0A, 0x28, 0x32, 0x44,
           0x42, 0x06, 0x0E, 0x12, 0x14, 0x17])

# Negative Voltage Gamma
send_cmd(0xE1)
send_data([0xD0, 0x00, 0x02, 0x07, 0x0A, 0x28, 0x31, 0x54,
           0x47, 0x0E, 0x1C, 0x17, 0x1B, 0x1E])

# Display Inversion ON (quan trọng cho hầu hết ST7789)
send_cmd(0x21)

# Normal Display Mode ON
send_cmd(0x13)
time.sleep(0.01)

# Display ON
send_cmd(0x29)
time.sleep(0.12)

print("    ✓ ST7789 initialized!")

# ============ TEST FILL MÀU ============
def fill_color(r, g, b, name):
    """Fill toàn màn hình với màu RGB"""
    print(f"[5] Fill màu: {name} (R={r}, G={g}, B={b})")
    
    # Set column address (0-239)
    send_cmd(0x2A)
    send_data([0x00, 0x00, 0x00, 0xEF])
    
    # Set row address (0-239)
    send_cmd(0x2B)
    send_data([0x00, 0x00, 0x00, 0xEF])
    
    # Write to RAM
    send_cmd(0x2C)
    
    # Convert RGB888 to RGB565
    c565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    high = (c565 >> 8) & 0xFF
    low = c565 & 0xFF
    
    # Tạo buffer cho 240x240 pixels
    pixel_count = 240 * 240
    buffer = [high, low] * pixel_count
    send_data(buffer)
    print(f"    → Sent {len(buffer)} bytes")

# Test các màu
fill_color(255, 0, 0, "ĐỎ")
time.sleep(2)

fill_color(0, 255, 0, "XANH LÁ")
time.sleep(2)

fill_color(0, 0, 255, "XANH DƯƠNG")
time.sleep(2)

fill_color(255, 255, 255, "TRẮNG")

print("\n" + "=" * 55)
print(" TEST HOÀN TẤT!")
print("=" * 55)
print("\nKết quả:")
print("  - Nếu thấy 4 màu → SPI hoạt động tốt!")
print("  - Nếu không thấy gì → Kiểm tra:")
print("    1. Thử đổi DC_PIN và RST_PIN (24 ↔ 25)")
print("    2. Kiểm tra kết nối dây MOSI, SCLK")
print("    3. Màn hình có thể cần offset đặc biệt")
print("\nNhấn Ctrl+C để thoát...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nCleaning up...")
    spi.close()
    GPIO.cleanup()
    print("Done!")
