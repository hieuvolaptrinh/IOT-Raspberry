#!/usr/bin/env python3
"""
PLAY VIDEO - ST7789 LCD với SPI Mode 3
Tốc độ ổn định, không bị lỗi màu
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
SPI_SPEED = 40000000  # Giảm về 40MHz cho ổn định

# Setup
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

def send_cmd(cmd):
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.xfer2([cmd])

def send_data(data):
    GPIO.output(DC_PIN, GPIO.HIGH)
    spi.xfer2(data)

def init_display():
    # Reset
    GPIO.output(RST_PIN, GPIO.HIGH); time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.LOW); time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.HIGH); time.sleep(0.2)
    
    send_cmd(0x01); time.sleep(0.15)  # SW Reset
    send_cmd(0x11); time.sleep(0.15)  # Sleep Out
    send_cmd(0x36); send_data([0x00])  # MADCTL
    send_cmd(0x3A); send_data([0x55])  # 16-bit color
    send_cmd(0x21)  # Inversion ON
    send_cmd(0x13); time.sleep(0.01)
    send_cmd(0x29); time.sleep(0.15)  # Display ON

def display_frame(frame):
    # Resize
    frame = cv2.resize(frame, (240, 240), interpolation=cv2.INTER_NEAREST)
    
    # BGR to RGB565
    r = (frame[:, :, 2] >> 3).astype(np.uint16)
    g = (frame[:, :, 1] >> 2).astype(np.uint16)
    b = (frame[:, :, 0] >> 3).astype(np.uint16)
    rgb565 = (r << 11) | (g << 5) | b
    
    # To bytes
    high = ((rgb565 >> 8) & 0xFF).astype(np.uint8)
    low = (rgb565 & 0xFF).astype(np.uint8)
    buffer = np.dstack((high, low)).flatten().tolist()
    
    # Set window + Write RAM
    send_cmd(0x2A); send_data([0x00, 0x00, 0x00, 0xEF])
    send_cmd(0x2B); send_data([0x00, 0x00, 0x00, 0xEF])
    send_cmd(0x2C)
    
    # Gửi data
    for i in range(0, len(buffer), 4096):
        spi.xfer2(buffer[i:i+4096])

print("Khởi tạo màn hình...")
init_display()

cap = cv2.VideoCapture("video.mp4")
if not cap.isOpened():
    print("Không mở được video.mp4!")
    GPIO.cleanup()
    exit(1)

print("Đang phát video... (Ctrl+C để dừng)")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        display_frame(frame)
        time.sleep(0.01)  # Delay nhỏ để ổn định

except KeyboardInterrupt:
    print("\nĐã dừng.")
finally:
    cap.release()
    spi.close()
    GPIO.cleanup()