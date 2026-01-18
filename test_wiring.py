#!/usr/bin/env python3
"""
KIỂM TRA DÂY NỐI - Xem dây có tiếp xúc tốt không
Test từng chân GPIO một và quan sát phản hồi
"""
import RPi.GPIO as GPIO
import time

# GPIO pins
pins = {
    18: "BL (Backlight) - Pin 12",
    24: "DC - Pin 18", 
    25: "RST - Pin 22",
}

print("="*55)
print(" KIỂM TRA TIẾP XÚC DÂY NỐI")
print(" Quan sát LED/đèn hoặc dùng đồng hồ đo")
print("="*55)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup all pins
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

print("\n📌 Bắt đầu test từng chân...")
print("   Quan sát đồng hồ đo hoặc đèn LED")

# Test 1: Backlight (dễ thấy nhất)
print("\n" + "-"*40)
print("[TEST 1] BACKLIGHT (GPIO 18 / Pin 12)")
print("-"*40)
print("Nếu dây BL nối đúng, đèn nền sẽ nhấp nháy")
for i in range(5):
    print(f"  Nhấp nháy {i+1}/5...")
    GPIO.output(18, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(18, GPIO.LOW)
    time.sleep(0.5)

GPIO.output(18, GPIO.HIGH)  # Bật lại
answer = input("❓ Đèn nền có nhấp nháy không? (y/n): ").strip().lower()
if answer == 'y':
    print("✅ BL: Dây nối OK!")
else:
    print("❌ BL: Dây không tiếp xúc hoặc nối sai!")
    print("   → Kiểm tra: BL (LCD) → Pin 12 (Pi)")

# Test 2: RST
print("\n" + "-"*40)
print("[TEST 2] RESET (GPIO 25 / Pin 22)")
print("-"*40)
print("Dùng đồng hồ đo chân RST trên LCD")
print("Phải thấy điện áp thay đổi 0V ↔ 3.3V")
for i in range(5):
    print(f"  Toggle {i+1}/5...")
    GPIO.output(25, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(25, GPIO.LOW)
    time.sleep(0.5)

GPIO.output(25, GPIO.HIGH)
input("Nhấn Enter để tiếp tục...")

# Test 3: DC
print("\n" + "-"*40)
print("[TEST 3] DC (GPIO 24 / Pin 18)")
print("-"*40)
print("Dùng đồng hồ đo chân DC trên LCD")
for i in range(5):
    print(f"  Toggle {i+1}/5...")
    GPIO.output(24, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(24, GPIO.LOW)
    time.sleep(0.5)

GPIO.output(24, GPIO.HIGH)
input("Nhấn Enter để tiếp tục...")

# Test 4: SPI (MOSI và SCK)
print("\n" + "-"*40)
print("[TEST 4] SPI DATA (GPIO 10, 11)")
print("-"*40)
print("Test SPI bằng cách gửi data")

try:
    import spidev
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 100000  # Chậm để dễ đo
    
    print("Gửi 10 byte qua SPI...")
    print("Dùng đồng hồ đo Pin 19 (SDA) và Pin 23 (SCL)")
    for i in range(10):
        spi.xfer2([0xAA, 0x55, 0xFF, 0x00])
        time.sleep(0.1)
    
    spi.close()
    print("✅ SPI data đã gửi")
except Exception as e:
    print(f"❌ Lỗi SPI: {e}")

# Tổng kết
print("\n" + "="*55)
print(" TỔNG KẾT")
print("="*55)
print("""
Nếu BACKLIGHT nhấp nháy → Ít nhất BL, VCC, GND nối OK

Nếu BACKLIGHT KHÔNG nhấp nháy:
  1. Kiểm tra VCC có nối vào 3.3V (Pin 1) không
  2. Kiểm tra GND có nối vào GND (Pin 6) không
  3. Kiểm tra BL có nối vào GPIO 18 (Pin 12) không
  4. Thử đổi dây jumper khác (có thể dây đứt)

Nếu Backlight OK nhưng LCD không hiển thị màu:
  1. Kiểm tra SCL nối vào Pin 23
  2. Kiểm tra SDA nối vào Pin 19
  3. Kiểm tra DC nối vào Pin 18
  4. Kiểm tra RST nối vào Pin 22
  5. Kiểm tra CS nối vào Pin 24
""")

GPIO.cleanup()
print("\nDone!")
