#!/usr/bin/env python3
"""
KIỂM TRA ĐẦY ĐỦ DÂY NỐI LCD ST7789
Chạy: python3 test_lcd_connection.py
"""
import time
import sys

print("="*55)
print(" KIỂM TRA KẾT NỐI LCD ST7789 - Raspberry Pi")
print("="*55)

# ========== 1. KIỂM TRA THƯ VIỆN ==========
print("\n[1] KIỂM TRA THƯ VIỆN...")

libs_ok = True
try:
    import RPi.GPIO as GPIO
    print("  ✅ RPi.GPIO: OK")
except ImportError:
    print("  ❌ RPi.GPIO: THIẾU")
    print("     Cài: pip3 install RPi.GPIO --break-system-packages")
    libs_ok = False

try:
    import spidev
    print("  ✅ spidev: OK")
except ImportError:
    print("  ❌ spidev: THIẾU")
    print("     Cài: pip3 install spidev --break-system-packages")
    libs_ok = False

try:
    from PIL import Image
    print("  ✅ Pillow: OK")
except ImportError:
    print("  ❌ Pillow: THIẾU")
    print("     Cài: pip3 install pillow --break-system-packages")
    libs_ok = False

if not libs_ok:
    print("\n⚠️  Vui lòng cài đủ thư viện trước!")
    sys.exit(1)

# ========== 2. KIỂM TRA SPI ==========
print("\n[2] KIỂM TRA SPI...")

import os
spi_ok = False
for dev in ["/dev/spidev0.0", "/dev/spidev0.1"]:
    if os.path.exists(dev):
        print(f"  ✅ Tìm thấy: {dev}")
        spi_ok = True

if not spi_ok:
    print("  ❌ Không tìm thấy SPI device!")
    print("  💡 Chạy: sudo raspi-config → Interface → SPI → Enable")
    sys.exit(1)

# Test SPI transfer
try:
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 4000000
    spi.xfer2([0xAA, 0x55])
    spi.close()
    print("  ✅ SPI transfer: OK")
except Exception as e:
    print(f"  ❌ SPI transfer: LỖI - {e}")
    sys.exit(1)

# ========== 3. KIỂM TRA GPIO ==========
print("\n[3] KIỂM TRA GPIO...")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

gpio_pins = {
    24: ("DC", "Pin 18"),
    25: ("RST", "Pin 22"),
    18: ("BL (Backlight)", "Pin 12"),
}

gpio_ok = True
for pin, (name, physical) in gpio_pins.items():
    try:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(pin, GPIO.LOW)
        print(f"  ✅ GPIO {pin} ({name} - {physical}): OK")
    except Exception as e:
        print(f"  ❌ GPIO {pin} ({name}): LỖI - {e}")
        gpio_ok = False

# ========== 4. TEST BACKLIGHT ==========
print("\n[4] TEST BACKLIGHT...")
print("  🔦 Bật backlight (GPIO 18)...")
GPIO.setup(18, GPIO.OUT)
GPIO.output(18, GPIO.HIGH)
time.sleep(1)

print("  🔦 Tắt backlight...")
GPIO.output(18, GPIO.LOW)
time.sleep(0.5)

print("  🔦 Bật lại backlight...")
GPIO.output(18, GPIO.HIGH)

answer = input("  ❓ Đèn nền LCD có nhấp nháy không? (y/n): ").strip().lower()
if answer == 'y':
    print("  ✅ Backlight: OK")
    bl_ok = True
else:
    print("  ⚠️  Backlight không phản hồi")
    print("      Kiểm tra: BL nối vào GPIO 18 (Pin 12)?")
    bl_ok = False

# ========== 5. HIỂN THỊ SƠ ĐỒ NỐI DÂY ==========
print("\n[5] SƠ ĐỒ NỐI DÂY CHUẨN:")
print("  ┌─────────┬───────────┬──────────────┐")
print("  │ LCD Pin │ GPIO(BCM) │ Physical Pin │")
print("  ├─────────┼───────────┼──────────────┤")
print("  │ VCC     │ 3.3V      │ Pin 1        │")
print("  │ GND     │ GND       │ Pin 6        │")
print("  │ SCL     │ GPIO 11   │ Pin 23       │")
print("  │ SDA     │ GPIO 10   │ Pin 19       │")
print("  │ RES     │ GPIO 25   │ Pin 22       │")
print("  │ DC      │ GPIO 24   │ Pin 18       │")
print("  │ CS      │ GPIO 8    │ Pin 24       │")
print("  │ BL      │ GPIO 18   │ Pin 12       │")
print("  └─────────┴───────────┴──────────────┘")

# ========== 6. HIỂN THỊ VỊ TRÍ PIN ==========
print("\n[6] VỊ TRÍ PIN TRÊN RASPBERRY PI:")
print("  ┌─────────────────────────────────┐")
print("  │      3.3V (1)  ●  ●  (2) 5V     │ ← VCC vào Pin 1")
print("  │           (3)  ●  ●  (4)        │")
print("  │           (5)  ●  ●  (6) GND    │ ← GND vào Pin 6")
print("  │           (7)  ●  ●  (8)        │")
print("  │           (9)  ●  ● (10)        │")
print("  │          (11)  ●  ● (12) BL     │ ← BL vào Pin 12")
print("  │          (13)  ●  ● (14)        │")
print("  │          (15)  ●  ● (16)        │")
print("  │      3.3V(17)  ●  ● (18) DC     │ ← DC vào Pin 18")
print("  │  SDA/MOSI(19)  ●  ● (20)        │ ← SDA vào Pin 19")
print("  │          (21)  ●  ● (22) RST    │ ← RES vào Pin 22")
print("  │  SCL/SCLK(23)  ●  ● (24) CS     │ ← SCL Pin 23, CS Pin 24")
print("  │          (25)  ●  ● (26)        │")
print("  └─────────────────────────────────┘")

# ========== KẾT QUẢ ==========
print("\n" + "="*55)
print(" KẾT QUẢ KIỂM TRA")
print("="*55)
print(f"  Thư viện : ✅ OK")
print(f"  SPI      : ✅ OK")
print(f"  GPIO     : {'✅ OK' if gpio_ok else '❌ LỖI'}")
print(f"  Backlight: {'✅ OK' if bl_ok else '⚠️  Chưa xác nhận'}")

if libs_ok and spi_ok and gpio_ok and bl_ok:
    print("\n🎉 TẤT CẢ KIỂM TRA OK!")
    print("   Chạy: python3 test_luma.py để test LCD")
else:
    print("\n⚠️  CÒN VẤN ĐỀ CẦN KHẮC PHỤC!")
    print("   Xem chi tiết lỗi ở trên.")

GPIO.cleanup()
