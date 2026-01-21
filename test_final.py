#!/usr/bin/env python3
"""
TEST CUỐI CÙNG - Thử tất cả SPI Mode và tốc độ chậm
"""
import spidev
import RPi.GPIO as GPIO
import time

DC_PIN = 24
RST_PIN = 25
BL_PIN = 18

print("=" * 60)
print(" TEST TẤT CẢ SPI MODE VÀ TỐC ĐỘ")
print("=" * 60)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)

def send_cmd(spi, cmd):
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.xfer2([cmd])

def send_data(spi, data):
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(data, int):
        spi.xfer2([data])
    else:
        for i in range(0, len(data), 4096):
            spi.xfer2(list(data)[i:i+4096])

def reset():
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.2)

def init_display(spi):
    reset()
    send_cmd(spi, 0x01); time.sleep(0.15)  # SW Reset
    send_cmd(spi, 0x11); time.sleep(0.15)  # Sleep Out
    send_cmd(spi, 0x36); send_data(spi, 0x00)  # MADCTL
    send_cmd(spi, 0x3A); send_data(spi, 0x55)  # 16-bit color
    send_cmd(spi, 0x21)  # Inversion ON
    send_cmd(spi, 0x13); time.sleep(0.01)  # Normal mode
    send_cmd(spi, 0x29); time.sleep(0.15)  # Display ON

def fill_red(spi):
    send_cmd(spi, 0x2A)
    send_data(spi, [0x00, 0x00, 0x00, 0xEF])
    send_cmd(spi, 0x2B)
    send_data(spi, [0x00, 0x00, 0x00, 0xEF])
    send_cmd(spi, 0x2C)
    # Red in RGB565 = 0xF800
    buffer = [0xF8, 0x00] * (240 * 240)
    send_data(spi, buffer)

# Test tất cả SPI modes và speeds
SPI_MODES = [0, 1, 2, 3]
SPI_SPEEDS = [1000000, 4000000, 10000000, 20000000]  # 1MHz, 4MHz, 10MHz, 20MHz

test_num = 0
total = len(SPI_MODES) * len(SPI_SPEEDS)

print(f"\nSẽ thử {total} cấu hình SPI khác nhau")
print("Nhấn Enter để bắt đầu...")
input()

for mode in SPI_MODES:
    for speed in SPI_SPEEDS:
        test_num += 1
        speed_mhz = speed / 1_000_000
        print(f"\n[{test_num}/{total}] Mode={mode}, Speed={speed_mhz}MHz")
        
        try:
            spi = spidev.SpiDev()
            spi.open(0, 0)
            spi.max_speed_hz = speed
            spi.mode = mode
            
            init_display(spi)
            fill_red(spi)
            
            spi.close()
            
            answer = input("    Thấy màu ĐỎ không? (y/Enter/q): ").strip().lower()
            if answer == 'y':
                print(f"\n{'='*60}")
                print(f" 🎉 THÀNH CÔNG!")
                print(f"    SPI_MODE = {mode}")
                print(f"    SPI_SPEED = {speed} ({speed_mhz}MHz)")
                print(f"{'='*60}")
                GPIO.cleanup()
                exit(0)
            elif answer == 'q':
                break
                
        except Exception as e:
            print(f"    Lỗi: {e}")

print("\n" + "=" * 60)
print(" ❌ KHÔNG THÀNH CÔNG")
print("=" * 60)
print("""
Kết luận: Màn hình của bạn cần LEVEL SHIFTER 3.3V → 5V

Mua level shifter 4 kênh hoặc 8 kênh, nối:
  - LV (Low Voltage) ← 3.3V từ Pi
  - HV (High Voltage) ← 5V từ Pi
  
  Các kênh:
  - MOSI: Pi GPIO10 → LV1 → HV1 → LCD SDA
  - CLK:  Pi GPIO11 → LV2 → HV2 → LCD SCL
  - DC:   Pi GPIO24 → LV3 → HV3 → LCD DC
  - RST:  Pi GPIO25 → LV4 → HV4 → LCD RST
  
  Các chân KHÔNG cần level shift:
  - VCC: nối thẳng 5V hoặc 3.3V (tùy LCD)
  - GND: nối thẳng
  - BL: có thể nối thẳng hoặc qua level shifter
  - CS: nối GND hoặc CE0
""")

GPIO.cleanup()
