#!/usr/bin/env python3
"""
Script kiểm tra kết nối LCD ST7789 với Raspberry Pi Zero 2 WH
Chạy: python3 test_lcd_connection.py
"""

import sys
import time

# ========== 1. KIỂM TRA SPI ==========
def check_spi():
    print("\n[1] KIỂM TRA SPI...")
    try:
        import os
        # Kiểm tra SPI device có tồn tại không
        spi_devices = ["/dev/spidev0.0", "/dev/spidev0.1"]
        found = False
        for dev in spi_devices:
            if os.path.exists(dev):
                print(f"  ✅ Tìm thấy SPI device: {dev}")
                found = True
        
        if not found:
            print("  ❌ KHÔNG tìm thấy SPI device!")
            print("  💡 Giải pháp: Chạy 'sudo raspi-config' -> Interface Options -> SPI -> Enable")
            return False
        
        # Thử import spidev
        import spidev
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 1000000
        spi.close()
        print("  ✅ SPI library hoạt động bình thường")
        return True
        
    except ImportError:
        print("  ❌ Không tìm thấy thư viện spidev!")
        print("  💡 Giải pháp: pip3 install spidev")
        return False
    except Exception as e:
        print(f"  ❌ Lỗi SPI: {e}")
        return False

# ========== 2. KIỂM TRA GPIO ==========
def check_gpio():
    print("\n[2] KIỂM TRA GPIO...")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Cấu hình GPIO theo file test_video.py
        gpio_pins = {
            24: "DC (Data/Command)",
            25: "RST (Reset)", 
            18: "BL (Backlight)"
        }
        
        all_ok = True
        for pin, name in gpio_pins.items():
            try:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(0.1)
                GPIO.output(pin, GPIO.LOW)
                print(f"  ✅ GPIO {pin} ({name}): OK")
            except Exception as e:
                print(f"  ❌ GPIO {pin} ({name}): LỖI - {e}")
                all_ok = False
        
        GPIO.cleanup()
        return all_ok
        
    except ImportError:
        print("  ❌ Không tìm thấy thư viện RPi.GPIO!")
        print("  💡 Giải pháp: pip3 install RPi.GPIO")
        return False
    except Exception as e:
        print(f"  ❌ Lỗi GPIO: {e}")
        return False

# ========== 3. KIỂM TRA BACKLIGHT ==========
def test_backlight():
    print("\n[3] TEST BACKLIGHT...")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(18, GPIO.OUT)
        
        print("  🔦 Bật backlight...")
        GPIO.output(18, GPIO.HIGH)
        time.sleep(2)
        
        print("  🔦 Tắt backlight...")
        GPIO.output(18, GPIO.LOW)
        time.sleep(1)
        
        print("  🔦 Bật lại backlight...")
        GPIO.output(18, GPIO.HIGH)
        
        answer = input("  ❓ Bạn có thấy đèn nền LCD nhấp nháy không? (y/n): ").strip().lower()
        GPIO.cleanup()
        
        if answer == 'y':
            print("  ✅ Backlight hoạt động!")
            return True
        else:
            print("  ⚠️  Backlight có thể đang được nối trực tiếp vào 3.3V")
            print("      (Điều này không phải lỗi nếu màn hình vẫn sáng)")
            return True
            
    except Exception as e:
        print(f"  ❌ Lỗi backlight: {e}")
        return False

# ========== 4. KIỂM TRA THƯ VIỆN ST7789 ==========
def check_st7789_library():
    print("\n[4] KIỂM TRA THƯ VIỆN ST7789...")
    try:
        import st7789
        print("  ✅ st7789 library đã được cài đặt")
        return True
    except ImportError:
        print("  ❌ Không tìm thấy thư viện st7789!")
        print("  💡 Giải pháp: pip3 install st7789")
        return False

# ========== 5. TEST HIỂN THỊ MÀU ==========
def test_display():
    print("\n[5] TEST HIỂN THỊ MÀU TRÊN LCD...")
    try:
        import st7789
        from PIL import Image
        
        # Khởi tạo màn hình với cấu hình giống test_video.py
        print("  🖥️  Đang khởi tạo LCD...")
        disp = st7789.ST7789(
            port=0,
            cs=0,           # Pin 24 -> CE0 (SPI)
            dc=24,          # Pin 18 -> GPIO 24 (BCM)
            rst=25,         # Pin 22 -> GPIO 25 (BCM)
            backlight=18,   # Pin 12 -> GPIO 18 (BCM)
            spi_speed_hz=40 * 1000 * 1000  # Giảm tốc độ để ổn định hơn
        )
        disp.begin()
        
        colors = [
            ((255, 0, 0), "ĐỎ"),
            ((0, 255, 0), "XANH LÁ"),
            ((0, 0, 255), "XANH DƯƠNG"),
            ((255, 255, 255), "TRẮNG"),
            ((0, 0, 0), "ĐEN")
        ]
        
        for color, name in colors:
            print(f"  🎨 Hiển thị màu {name}...")
            img = Image.new('RGB', (240, 240), color)
            disp.display(img)
            time.sleep(1)
        
        print("\n  ✅ Test hiển thị hoàn tất!")
        answer = input("  ❓ Bạn có thấy các màu thay đổi trên LCD không? (y/n): ").strip().lower()
        
        if answer == 'y':
            print("\n" + "="*50)
            print("  ✅ KẾT NỐI LCD THÀNH CÔNG!")
            print("="*50)
            return True
        else:
            print("\n  ❌ LCD không hiển thị đúng!")
            print("  💡 Kiểm tra lại:")
            print("     - Dây nối SDA (MOSI) vào GPIO 10 (Pin 19)")
            print("     - Dây nối SCL (SCLK) vào GPIO 11 (Pin 23)")
            print("     - Dây nối DC vào GPIO 24 (Pin 18)")
            print("     - Dây nối RST vào GPIO 25 (Pin 22)")
            print("     - Dây nối CS vào CE0 GPIO 8 (Pin 24)")
            return False
            
    except Exception as e:
        print(f"  ❌ Lỗi hiển thị: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========== MAIN ==========
def main():
    print("="*50)
    print(" KIỂM TRA KẾT NỐI LCD ST7789 - Raspberry Pi Zero 2 WH")
    print("="*50)
    
    print("\n📌 Sơ đồ kết nối cần có:")
    print("   LCD Pin   ->  Raspberry Pi Pin")
    print("   ─────────────────────────────────")
    print("   VCC       ->  3.3V (Pin 1)")
    print("   GND       ->  GND  (Pin 6)")
    print("   SCL/SCLK  ->  GPIO 11 (Pin 23)")
    print("   SDA/MOSI  ->  GPIO 10 (Pin 19)")
    print("   RES/RST   ->  GPIO 25 (Pin 22)")
    print("   DC        ->  GPIO 24 (Pin 18)")
    print("   CS        ->  CE0/GPIO 8 (Pin 24)")
    print("   BL        ->  GPIO 18 (Pin 12) hoặc 3.3V")
    
    results = []
    
    # Chạy các bài test
    results.append(("SPI", check_spi()))
    results.append(("GPIO", check_gpio()))
    results.append(("ST7789 Library", check_st7789_library()))
    results.append(("Backlight", test_backlight()))
    results.append(("Display", test_display()))
    
    # Tổng kết
    print("\n" + "="*50)
    print(" KẾT QUẢ KIỂM TRA")
    print("="*50)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 TẤT CẢ KIỂM TRA ĐỀU THÀNH CÔNG!")
        print("   LCD đã kết nối và hoạt động bình thường.")
    else:
        print("\n⚠️  CÓ MỘT SỐ VẤN ĐỀ CẦN KHẮC PHỤC!")
        print("   Xem chi tiết lỗi ở trên để sửa.")

if __name__ == "__main__":
    main()
