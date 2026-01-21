#!/usr/bin/env python3
"""
TEST TẤT CẢ CẤU HÌNH cho màn hình Trung Quốc ST7789 1.54" v1.1
Thử từng offset, rotation, invert để tìm config đúng
"""
import spidev
import RPi.GPIO as GPIO
import time

print("=" * 60)
print(" BRUTE FORCE TEST - Màn hình TQ ST7789 1.54\" v1.1")
print("=" * 60)

# ============ THỬ CẢ 2 CONFIG DC/RST ============
DC_RST_CONFIGS = [
    (24, 25, "DC=24, RST=25"),
    (25, 24, "DC=25, RST=24"),
]

BL_PIN = 18

# ============ CÁC OFFSET PHỔ BIẾN CHO MÀN HÌNH TQ 1.54" ============
OFFSETS = [
    (0, 0, "No offset"),
    (1, 26, "TQ Generic 1"),
    (2, 1, "TQ Generic 2"),
    (0, 80, "240x240 to 240x320"),
    (80, 0, "Alt offset"),
    (52, 40, "Some TQ displays"),
    (40, 52, "Some TQ displays 2"),
    (0, 35, "Waveshare-like"),
]

# Setup SPI
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 40000000
spi.mode = 0

def send_cmd(dc_pin, cmd):
    GPIO.output(dc_pin, GPIO.LOW)
    spi.xfer2([cmd])

def send_data(dc_pin, data):
    GPIO.output(dc_pin, GPIO.HIGH)
    if isinstance(data, int):
        spi.xfer2([data])
    else:
        data = list(data)
        for i in range(0, len(data), 4096):
            spi.xfer2(data[i:i+4096])

def reset(rst_pin):
    GPIO.output(rst_pin, GPIO.HIGH)
    time.sleep(0.01)
    GPIO.output(rst_pin, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(rst_pin, GPIO.HIGH)
    time.sleep(0.15)

def init_display(dc_pin, rst_pin, invert=True):
    reset(rst_pin)
    
    send_cmd(dc_pin, 0x01)  # Software Reset
    time.sleep(0.15)
    
    send_cmd(dc_pin, 0x11)  # Sleep Out
    time.sleep(0.12)
    
    send_cmd(dc_pin, 0x36)  # MADCTL
    send_data(dc_pin, 0x00)
    
    send_cmd(dc_pin, 0x3A)  # Pixel Format
    send_data(dc_pin, 0x55)
    
    send_cmd(dc_pin, 0xB2)  # Porch Setting
    send_data(dc_pin, [0x0C, 0x0C, 0x00, 0x33, 0x33])
    
    send_cmd(dc_pin, 0xB7)  # Gate Control
    send_data(dc_pin, 0x35)
    
    send_cmd(dc_pin, 0xBB)  # VCOM
    send_data(dc_pin, 0x28)
    
    send_cmd(dc_pin, 0xC0)  # LCM Control
    send_data(dc_pin, 0x0C)
    
    send_cmd(dc_pin, 0xC2)  # VDV VRH Enable
    send_data(dc_pin, [0x01, 0xFF])
    
    send_cmd(dc_pin, 0xC3)  # VRH Set
    send_data(dc_pin, 0x10)
    
    send_cmd(dc_pin, 0xC4)  # VDV Set
    send_data(dc_pin, 0x20)
    
    send_cmd(dc_pin, 0xC6)  # Frame Rate
    send_data(dc_pin, 0x0F)
    
    send_cmd(dc_pin, 0xD0)  # Power Control
    send_data(dc_pin, [0xA4, 0xA1])
    
    # Display Inversion
    if invert:
        send_cmd(dc_pin, 0x21)  # Inversion ON
    else:
        send_cmd(dc_pin, 0x20)  # Inversion OFF
    
    send_cmd(dc_pin, 0x13)  # Normal Mode
    time.sleep(0.01)
    
    send_cmd(dc_pin, 0x29)  # Display ON
    time.sleep(0.12)

def fill_color(dc_pin, x_off, y_off, r, g, b):
    # Column Address (với offset)
    x_start = x_off
    x_end = x_off + 239
    send_cmd(dc_pin, 0x2A)
    send_data(dc_pin, [x_start >> 8, x_start & 0xFF, x_end >> 8, x_end & 0xFF])
    
    # Row Address (với offset)
    y_start = y_off
    y_end = y_off + 239
    send_cmd(dc_pin, 0x2B)
    send_data(dc_pin, [y_start >> 8, y_start & 0xFF, y_end >> 8, y_end & 0xFF])
    
    # Write RAM
    send_cmd(dc_pin, 0x2C)
    
    # RGB565
    c565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    high = (c565 >> 8) & 0xFF
    low = c565 & 0xFF
    
    buffer = [high, low] * (240 * 240)
    send_data(dc_pin, buffer)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)

test_num = 0
total_tests = len(DC_RST_CONFIGS) * len(OFFSETS) * 2  # x2 cho invert

print(f"\nSẽ thử {total_tests} cấu hình khác nhau.")
print("Mỗi config sẽ hiện màu ĐỎ, XANH, TRẮNG")
print("Nhấn Enter để tiếp tục, 'y' nếu thấy màu đúng, 'q' để thoát\n")
input("Nhấn Enter để bắt đầu...")

try:
    for dc_pin, rst_pin, dc_rst_name in DC_RST_CONFIGS:
        GPIO.setup(dc_pin, GPIO.OUT)
        GPIO.setup(rst_pin, GPIO.OUT)
        
        for invert in [True, False]:
            for x_off, y_off, offset_name in OFFSETS:
                test_num += 1
                print(f"\n[{test_num}/{total_tests}] {dc_rst_name}")
                print(f"    Offset: ({x_off}, {y_off}) - {offset_name}")
                print(f"    Invert: {invert}")
                
                init_display(dc_pin, rst_pin, invert)
                
                # Test màu
                print("    → ĐỎ...")
                fill_color(dc_pin, x_off, y_off, 255, 0, 0)
                time.sleep(0.3)
                
                print("    → XANH...")
                fill_color(dc_pin, x_off, y_off, 0, 255, 0)
                time.sleep(0.3)
                
                print("    → TRẮNG...")
                fill_color(dc_pin, x_off, y_off, 255, 255, 255)
                
                answer = input("    Thấy màu chưa? (y=CÓ/Enter=tiếp/q=thoát): ").strip().lower()
                
                if answer == 'y':
                    print("\n" + "=" * 60)
                    print(" 🎉 TÌM THẤY CẤU HÌNH ĐÚNG!")
                    print("=" * 60)
                    print(f"  DC_PIN = {dc_pin}")
                    print(f"  RST_PIN = {rst_pin}")
                    print(f"  OFFSET_X = {x_off}")
                    print(f"  OFFSET_Y = {y_off}")
                    print(f"  INVERT = {invert}")
                    print("=" * 60)
                    spi.close()
                    GPIO.cleanup()
                    exit(0)
                elif answer == 'q':
                    print("\nThoát...")
                    spi.close()
                    GPIO.cleanup()
                    exit(0)

    print("\n" + "=" * 60)
    print(" ❌ Đã thử hết tất cả cấu hình mà không thành công")
    print("=" * 60)
    print("Có thể vấn đề là:")
    print("  1. Dây MOSI/SCLK nối sai (kiểm tra Pin 19 và 23)")
    print("  2. Màn hình cần 5V logic (cần level shifter)")
    print("  3. CS cần nối đúng (thử nối GND hoặc CE0)")
    
except KeyboardInterrupt:
    print("\n\nĐã dừng.")
finally:
    spi.close()
    GPIO.cleanup()
