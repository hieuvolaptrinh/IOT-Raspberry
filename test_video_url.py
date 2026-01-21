#!/usr/bin/env python3
"""
PLAY VIDEO FROM URL - ST7789 LCD | SPI Mode 3
==============================================
Stream video từ URL và hiển thị lên LCD 240x240

Chạy: sudo python3 test_video_url.py
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
SPI_SPEED = 32000000  # 32MHz

# URL VIDEO TEST
VIDEO_URL = "https://res.cloudinary.com/dpbgeejfl/video/upload/v1768989256/vsl_videos/vsl_20260121_165346_65091ca8.mp4"

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
    cmd(0x36); data(0x08)  # BGR order
    
    cmd(0x3A); data(0x55)  # 16-bit color (RGB565)
    
    cmd(0xB2); data([0x0C, 0x0C, 0x00, 0x33, 0x33])
    cmd(0xB7); data(0x35)
    cmd(0xBB); data(0x28)
    cmd(0xC0); data(0x0C)
    cmd(0xC2); data([0x01, 0xFF])
    cmd(0xC3); data(0x10)
    cmd(0xC4); data(0x20)
    cmd(0xC6); data(0x0F)
    cmd(0xD0); data([0xA4, 0xA1])
    
    cmd(0x21)  # Inversion ON
    cmd(0x13); time.sleep(0.01)
    cmd(0x29); time.sleep(0.12)  # Display ON

def show_frame(frame):
    """Hiển thị frame lên LCD"""
    frame = cv2.resize(frame, (240, 240), interpolation=cv2.INTER_NEAREST)
    
    # Convert BGR to RGB565
    b = frame[:, :, 0].astype(np.uint16)
    g = frame[:, :, 1].astype(np.uint16)
    r = frame[:, :, 2].astype(np.uint16)
    
    rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    
    buffer = np.empty((240, 240, 2), dtype=np.uint8)
    buffer[:, :, 0] = (rgb565 >> 8) & 0xFF
    buffer[:, :, 1] = rgb565 & 0xFF
    
    cmd(0x2A); data([0, 0, 0, 239])
    cmd(0x2B); data([0, 0, 0, 239])
    cmd(0x2C)
    
    data_bulk(buffer.flatten().tolist())

def show_message(text, color=(255, 255, 255)):
    """Hiển thị message lên LCD"""
    frame = np.zeros((240, 240, 3), dtype=np.uint8)
    
    # Vẽ text
    font = cv2.FONT_HERSHEY_SIMPLEX
    lines = text.split('\n')
    y = 100
    for line in lines:
        text_size = cv2.getTextSize(line, font, 0.6, 1)[0]
        x = (240 - text_size[0]) // 2
        cv2.putText(frame, line, (x, y), font, 0.6, color, 1)
        y += 30
    
    show_frame(frame)

# ============ PLAY VIDEO FROM URL ============
def play_video_from_url(url, loop=True):
    """Phát video từ URL"""
    print(f"🌐 Đang mở video từ URL...")
    print(f"📹 {url[:60]}...")
    
    show_message("Loading...\nPlease wait", (0, 255, 255))
    
    # OpenCV có thể mở video trực tiếp từ URL!
    cap = cv2.VideoCapture(url)
    
    if not cap.isOpened():
        print("❌ Lỗi: Không mở được video từ URL!")
        show_message("Error!\nCannot open URL", (0, 0, 255))
        return False
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"✅ Video: {fps:.0f} FPS, {total} frames")
    print("🎬 Đang phát... (Ctrl+C để dừng)")
    
    frame_count = 0
    start = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                if loop:
                    # Loop lại từ đầu
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    print("✅ Video kết thúc!")
                    break
            
            show_frame(frame)
            frame_count += 1
            
            if frame_count % 50 == 0:
                elapsed = time.time() - start
                real_fps = frame_count / elapsed
                print(f"FPS: {real_fps:.1f}", end="\r")
                
    except KeyboardInterrupt:
        elapsed = time.time() - start
        print(f"\n⏹️ Dừng. FPS trung bình: {frame_count/elapsed:.1f}")
    
    finally:
        cap.release()
    
    return True

# ============ MAIN ============
if __name__ == "__main__":
    print("=" * 50)
    print("📺 PLAY VIDEO FROM URL - ST7789 LCD")
    print("=" * 50)
    
    print("Khởi tạo LCD...")
    init_lcd()
    print("✅ LCD OK!")
    
    try:
        play_video_from_url(VIDEO_URL, loop=True)
    finally:
        spi.close()
        GPIO.cleanup()
        print("✅ Cleanup xong!")
