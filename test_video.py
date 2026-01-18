#!/usr/bin/env python3
"""
Test LCD ST7789 - Thử từng config một
Nhấn Enter để chuyển config tiếp theo
"""
import st7789
from PIL import Image
import time
import sys

PORT = 0
CS = 0          # CE0 (pin 24)
DC = 24         # GPIO24 (pin 18)
RST = 25        # GPIO25 (pin 22)
BL = 18         # GPIO18 (pin 12)

def show(disp, color, t=0.5):
    img = Image.new("RGB", (240, 240), color=color)
    disp.display(img)
    time.sleep(t)

def test_config(rot, inv, offl, offt, speed):
    """Test một config và hỏi user"""
    print(f"\n{'='*50}")
    print(f"Config: rot={rot}, invert={inv}, offset=({offl},{offt})")
    print(f"SPI Speed: {speed/1_000_000}MHz")
    print("="*50)
    
    try:
        disp = st7789.ST7789(
            port=PORT,
            cs=CS,
            dc=DC,
            rst=RST,
            backlight=BL,
            width=240,
            height=240,
            rotation=rot,
            invert=inv,
            spi_speed_hz=speed,
            offset_left=offl,
            offset_top=offt
        )
        disp.begin()
        
        print("Hien thi: DO...")
        show(disp, "red")
        print("Hien thi: XANH LA...")
        show(disp, "green")
        print("Hien thi: XANH DUONG...")
        show(disp, "blue")
        print("Hien thi: TRANG...")
        show(disp, "white")
        
        return disp, True
        
    except Exception as e:
        print(f"Loi: {e}")
        return None, False

def main():
    print("="*50)
    print(" TEST LCD ST7789 - Raspberry Pi")
    print(" Nhan Enter de thu config tiep theo")
    print(" Nhap 'q' de thoat")
    print("="*50)
    
    tests = [
        # (rotation, invert, offset_left, offset_top, spi_speed)
        (0,   True,  0,  0, 4_000_000),
        (0,   False, 0,  0, 4_000_000),
        (0,   True,  0, 80, 4_000_000),
        (0,   True, 80,  0, 4_000_000),
        (90,  True,  0,  0, 4_000_000),
        (180, True,  0,  0, 4_000_000),
        (0,   True,  0,  0, 10_000_000),
        (0,   True,  0,  0, 40_000_000),
    ]
    
    current_disp = None
    
    for i, (rot, inv, offl, offt, speed) in enumerate(tests):
        print(f"\n[TEST {i+1}/{len(tests)}]")
        
        # Test config
        disp, success = test_config(rot, inv, offl, offt, speed)
        
        if success:
            current_disp = disp
            answer = input("\nThay mau? (y=tim thay/Enter=tiep tuc/q=thoat): ").strip().lower()
            
            if answer == 'y':
                print(f"\n{'*'*50}")
                print(f"TIM THAY CONFIG DUNG!")
                print(f"rotation={rot}, invert={inv}")
                print(f"offset_left={offl}, offset_top={offt}")
                print(f"spi_speed_hz={speed}")
                print(f"{'*'*50}")
                break
            elif answer == 'q':
                print("Thoat...")
                break
        else:
            input("Loi! Nhan Enter de tiep tuc...")
    
    print("\nDone.")

if __name__ == "__main__":
    main()
