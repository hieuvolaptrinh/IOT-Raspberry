import os
import json
import time
from pybleno import Bleno, BlenoPrimaryService, Characteristic


def connect_wifi(ssid, password):
    print(f"Đang tiến hành kết nối vào WiFi: {ssid}...")
    # Lệnh nmcli để kết nối WiFi trên Raspberry Pi/Linux
    cmd = f'sudo nmcli dev wifi connect "{ssid}" password "{password}"'
    res = os.system(cmd)
    if res == 0:
        print("✅ Kết nối WiFi thành công!")
    else:
        print("❌ Kết nối WiFi thất bại! Hãy kiểm tra lại SSID và Mật khẩu.")

# 2. Định nghĩa BLE Characteristic để nhận cấu hình WiFi
class WifiSetupCharacteristic(Characteristic):
    def __init__(self):
        super().__init__({
            'uuid': 'abcd', # Định danh UUID cho việc ghi dữ liệu wifi
            'properties': ['write'],
            'value': None
        })

    def onWriteRequest(self, data, offset, withoutResponse, callback):
        try:
            # Dữ liệu gửi từ app/client sẽ ở dạng byte, cần giải mã ra string (utf-8)
            decoded = data.decode('utf-8')
            print(f"📥 Nhận được dữ liệu: {decoded}")
            
            # Phân tích chuỗi JSON
            wifi_info = json.loads(decoded)
            ssid = wifi_info.get("ssid")
            password = wifi_info.get("password")
            
            if ssid and password:
                # Phản hồi báo cho điện thoại biết đã nhận thành công
                callback(Characteristic.RESULT_SUCCESS)
                # Thực hiện kết nối vào mạng
                connect_wifi(ssid, password)
            else:
                callback(Characteristic.RESULT_UNLIKELY_ERROR)
        except Exception as e:
            print("Lỗi đọc hoặc phân tích dữ liệu JSON:", e)
            callback(Characteristic.RESULT_UNLIKELY_ERROR)

# --- CHƯƠNG TRÌNH CHÍNH ---

if __name__ == "__main__":
    print("🔴 Đang khởi động BLE Server (Luôn phát sóng)...")

    # Khởi tạo Bleno (BLE Server)
    bleno = Bleno()
    wifi_characteristic = WifiSetupCharacteristic()

    # Nhóm Characteristic vào Service với UUID 1234
    wifi_service = BlenoPrimaryService({
        'uuid': '1234',
        'characteristics': [wifi_characteristic]
    })

    def onStateChange(state):
        if state == 'poweredOn':
            print("📡 Bluetooth đã bật. Bắt đầu phát sóng BLE...")
            # Phát sóng với tên 'Pi-Setup' và Service UUID '1234'
            bleno.startAdvertising('Pi-Setup', ['1234'])
        else:
            print("Bluetooth đang tắt...")
            bleno.stopAdvertising()

    def onAdvertisingStart(error):
        if not error:
            print("✅ Đang phát sóng BLE (Advertising) thành công!")
            bleno.setServices([wifi_service])
        else:
            print(f"❌ Lỗi khi bắt đầu advertising: {error}")

    # Lắng nghe sự kiện
    bleno.on('stateChange', onStateChange)
    bleno.on('advertisingStart', onAdvertisingStart)

    # Chạy Server
    bleno.start()

    # Vòng lặp giữ cho script không bị tắt
    try:
        print("Nhấn Ctrl+C để tắt BLE Server.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Đang tắt BLE Server...")
        bleno.stopAdvertising()
        bleno.disconnect()