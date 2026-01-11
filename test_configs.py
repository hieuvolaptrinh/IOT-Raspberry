#!/usr/bin/env python3
"""
Test nhiều cấu hình: SPI mode, inversion, memory access
Màn hình chớp = đang nhận tín hiệu, chỉ cần tìm đúng cấu hình
"""

import spidev
import RPi.GPIO as GPIO
import time

DC_PIN = 24
RST_PIN = 25
CS_PIN = 8

print("="*50)
print("TEST NHIỀU CẤU HÌNH")
print("="*50)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(CS_PIN, GPIO.OUT)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 10000000  # 10MHz - chậm hơn nữa
spi.no_cs = True

def cmd(c):
    GPIO.output(CS_PIN, GPIO.LOW)
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.writebytes([c])
    GPIO.output(CS_PIN, GPIO.HIGH)

def data(d):
    GPIO.output(CS_PIN, GPIO.LOW)
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(d, int):
        spi.writebytes([d])
    else:
        for i in range(0, len(d), 4096):
            spi.writebytes(d[i:i+4096])
    GPIO.output(CS_PIN, GPIO.HIGH)

def reset():
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.2)

def init_lcd(madctl, use_inversion):
    reset()
    cmd(0x01)  # Software reset
    time.sleep(0.15)
    cmd(0x11)  # Sleep out
    time.sleep(0.12)
    cmd(0x36)  # Memory Access Control
    data(madctl)
    cmd(0x3A)  # Pixel format
    data(0x55)
    if use_inversion:
        cmd(0x21)  # Inversion ON
    else:
        cmd(0x20)  # Inversion OFF
    cmd(0x29)  # Display ON
    time.sleep(0.1)

def fill_red():
    cmd(0x2A)
    data([0x00, 0x00, 0x00, 0xEF])
    cmd(0x2B)
    data([0x00, 0x00, 0x00, 0xEF])
    cmd(0x2C)
    GPIO.output(CS_PIN, GPIO.LOW)
    GPIO.output(DC_PIN, GPIO.HIGH)
    red = [0xF8, 0x00] * 240
    for _ in range(240):
        spi.writebytes(red)
    GPIO.output(CS_PIN, GPIO.HIGH)

# Các cấu hình thử
configs = [
    (0, 0x00, True, "SPI mode 0, MADCTL 0x00, Inversion ON"),
    (0, 0x00, False, "SPI mode 0, MADCTL 0x00, Inversion OFF"),
    (0, 0x08, True, "SPI mode 0, MADCTL 0x08 (BGR), Inversion ON"),
    (0, 0x08, False, "SPI mode 0, MADCTL 0x08 (BGR), Inversion OFF"),
    (3, 0x00, True, "SPI mode 3, MADCTL 0x00, Inversion ON"),
    (3, 0x00, False, "SPI mode 3, MADCTL 0x00, Inversion OFF"),
    (2, 0x00, True, "SPI mode 2, MADCTL 0x00, Inversion ON"),
]

print("\nNhấn Enter sau mỗi test. Ghi nhớ cấu hình nào hiển thị màu ĐỎ!\n")

for spi_mode, madctl, inv, desc in configs:
    print(f"\n>>> Testing: {desc}")
    spi.mode = spi_mode
    init_lcd(madctl, inv)
    fill_red()
    print("    → Màn hình có hiển thị màu ĐỎ không? (y/n)")
    answer = input("    Nhập 'y' nếu thấy màu đỏ, 'n' nếu không, 'q' để thoát: ")
    if answer.lower() == 'y':
        print(f"\n✅ TÌM THẤY CẤU HÌNH ĐÚNG: {desc}")
        print(f"   SPI mode = {spi_mode}")
        print(f"   MADCTL = 0x{madctl:02X}")
        print(f"   Inversion = {'ON' if inv else 'OFF'}")
        break
    elif answer.lower() == 'q':
        break

spi.close()
GPIO.cleanup()
print("\nHoàn tất!")
