#!/usr/bin/env python3
"""
PLAY VIDEO - ST7789 LCD | SPI Mode 3
Đã fix: màu đúng, mượt, ổn định
"""
import cv2
import numpy as np
import spidev
import RPi.GPIO as GPIO
import time

# ============ CẤU HÌNH ============
DC_PIN = 24
RST_PIN = 25
BL_PIN = 18
SPI_MODE = 3
SPI_SPEED = 32000000  # 32MHz - cân bằng tốc độ và ổn định

# ============ SETUP ============
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = SPI_SPEED
spi.mode = SPI_MODE

# ============ LCD FUNCTIONS ============
def cmd(c):
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.xfer2([c])

def data(d):
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(d, list):
        spi.xfer2(d)
    else:
        spi.xfer2([d])

def data_bulk(d):
    """Gửi data lớn theo chunk"""
    GPIO.output(DC_PIN, GPIO.HIGH)
    for i in range(0, len(d), 4096):
        spi.xfer2(d[i:i+4096])

def init_lcd():
    # Hard reset
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.15)
    
    cmd(0x01); time.sleep(0.15)  # Software reset
    cmd(0x11); time.sleep(0.12)  # Sleep out
    
    # MADCTL - Memory Access Control
    # 0x08 = BGR order (fix màu đảo)
    cmd(0x36); data(0x08)
    
    cmd(0x3A); data(0x55)  # 16-bit color (RGB565)
    
    cmd(0xB2); data([0x0C, 0x0C, 0x00, 0x33, 0x33])  # Porch
    cmd(0xB7); data(0x35)  # Gate
    cmd(0xBB); data(0x28)  # VCOM
    cmd(0xC0); data(0x0C)  # LCM
    cmd(0xC2); data([0x01, 0xFF])
    cmd(0xC3); data(0x10)
    cmd(0xC4); data(0x20)
    cmd(0xC6); data(0x0F)
    cmd(0xD0); data([0xA4, 0xA1])
    
    cmd(0x21)  # Inversion ON
    cmd(0x13); time.sleep(0.01)  # Normal mode
    cmd(0x29); time.sleep(0.12)  # Display ON

def show_frame(frame):
    """Hiển thị frame lên LCD"""
    # Resize về 240x240
    frame = cv2.resize(frame, (240, 240), interpolation=cv2.INTER_NEAREST)
    
    # OpenCV dùng BGR, convert sang RGB565
    # RGB565: RRRRR GGGGGG BBBBB (16 bit)
    b = frame[:, :, 0].astype(np.uint16)
    g = frame[:, :, 1].astype(np.uint16)
    r = frame[:, :, 2].astype(np.uint16)
    
    rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    
    # Tách thành high/low bytes
    buffer = np.empty((240, 240, 2), dtype=np.uint8)
    buffer[:, :, 0] = (rgb565 >> 8) & 0xFF  # High byte
    buffer[:, :, 1] = rgb565 & 0xFF          # Low byte
    
    # Set window
    cmd(0x2A); data([0, 0, 0, 239])  # Column 0-239
    cmd(0x2B); data([0, 0, 0, 239])  # Row 0-239
    cmd(0x2C)  # Write RAM
    
    # Gửi pixels
    data_bulk(buffer.flatten().tolist())

# ============ MAIN ============
print("Khởi tạo LCD...")
init_lcd()
print("OK!")

# Mở video
cap = cv2.VideoCapture("video.mp4")
if not cap.isOpened():
    print("Lỗi: Không mở được video.mp4")
    spi.close()
    GPIO.cleanup()
    exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"Video: {fps:.0f} FPS, {total} frames")
print("Đang phát... (Ctrl+C để dừng)")

try:
    frame_count = 0
    start = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            # Loop lại từ đầu
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        
        show_frame(frame)
        frame_count += 1
        
        # Hiển thị FPS thực mỗi 50 frame
        if frame_count % 50 == 0:
            elapsed = time.time() - start
            real_fps = frame_count / elapsed
            print(f"FPS: {real_fps:.1f}", end="\r")

except KeyboardInterrupt:
    elapsed = time.time() - start
    print(f"\nDừng. FPS trung bình: {frame_count/elapsed:.1f}")

finally:
    cap.release()
    spi.close()
    GPIO.cleanup()
    print("Cleanup xong!")