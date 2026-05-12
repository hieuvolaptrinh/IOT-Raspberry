# 📡 Hướng Dẫn Cấu Hình WiFi Từ Xa Bằng BLE

Tài liệu này hướng dẫn cách cấu hình và chạy file `ble_server.py` để board (Raspberry Pi) luôn tự động phát sóng Bluetooth (BLE). Từ đó, bạn có thể dùng điện thoại hoặc máy tính kết nối vào board và cấu hình mạng WiFi bất cứ lúc nào.

> **Lưu ý:** Code sử dụng **BlueZ D-Bus API** — thư viện có sẵn trên Raspberry Pi OS, **không cần `pip install` thêm bất kỳ thư viện bên ngoài nào**.

---

## 🛠 BƯỚC 1 — Cài đặt các gói cần thiết trên mạch

Mở terminal trên Raspberry Pi và chạy các lệnh sau:

1. **Cài đặt gói Bluetooth hệ thống (thường đã có sẵn):**

   ```bash
   sudo apt-get update
   sudo apt-get install -y bluetooth bluez python3-dbus python3-gi
   ```

2. **Đảm bảo `NetworkManager` (nmcli) có sẵn để kết nối WiFi:**

   ```bash
   sudo apt-get install -y network-manager
   ```

3. **Bật Bluetooth adapter:**

   ```bash
   sudo hciconfig hci0 up
   ```

> ✅ **Không cần `pip install` gì cả!** Tất cả thư viện Python (`dbus`, `gi`) đều đi kèm với hệ điều hành Raspberry Pi OS.

---

## 💻 BƯỚC 2 — Cách hoạt động của `ble_server.py`

Mã nguồn `ble_server.py` sử dụng BlueZ D-Bus API (cách chính thức của Linux). Quy trình hoạt động:

1. **Khởi động**: Script đăng ký một GATT Service và BLE Advertisement với BlueZ qua D-Bus.
2. **Phát sóng**: Bluetooth luôn phát sóng với tên hiển thị **`Pi-Setup`**.
3. **Lắng nghe**: Service UUID `1234`, Characteristic UUID `abcd` chờ nhận dữ liệu.
4. **Nhận cấu hình**: Chờ nhận JSON: `{"ssid":"Tên_WiFi","password":"Mật_khẩu"}`.
5. **Kết nối WiFi**: Gọi `nmcli` để kết nối mạng. BLE vẫn tiếp tục phát sóng sau khi kết nối.

---

## 🚀 BƯỚC 3 — Cho BLE tự chạy khi khởi động

Để mạch luôn tự động phát BLE mỗi khi cắm điện, thiết lập Systemd service:

1. **Tạo service mới:**

   ```bash
   sudo nano /etc/systemd/system/ble-setup.service
   ```

2. **Dán nội dung sau vào file:**

   ```ini
   [Unit]
   Description=BLE WiFi Setup Service
   After=bluetooth.target
   Requires=bluetooth.target

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/IOT-Raspberry/ble/ble_server.py
   WorkingDirectory=/home/pi/IOT-Raspberry/ble
   Restart=always
   RestartSec=3
   User=root

   [Install]
   WantedBy=multi-user.target
   ```

   > ⚠️ **Lưu ý:** Thay đường dẫn `/home/pi/IOT-Raspberry/ble/ble_server.py` cho chính xác với vị trí file trên mạch của bạn.

3. **Lưu file (Ctrl+O, Enter, Ctrl+X) và bật service:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ble-setup
   sudo systemctl start ble-setup
   ```

4. **Kiểm tra trạng thái:**
   sudo systemctl enable ble-setup
   sudo systemctl start ble-setup

   ```bash
   sudo systemctl status ble-setup
   ```

   Nếu thấy dòng `Active: active (running)` là đã thành công ✅

👉 **Từ giờ:** Mỗi lần khởi động, Bluetooth sẽ luôn được phát để bạn có thể vào điều chỉnh mạng bất cứ lúc nào.

---

## 📱 BƯỚC 4 — Cách kết nối và thiết lập WiFi

Bất cứ lúc nào muốn kết nối mạch vào WiFi mới, bạn có thể dùng **điện thoại** hoặc **máy tính**.

### Cách 1: Dùng ứng dụng nRF Connect (Điện thoại)

1. Tải app **nRF Connect for Mobile** trên CH Play hoặc App Store.
2. Bật Bluetooth trên điện thoại, mở app **nRF Connect** và nhấn nút **Scan**.
3. Tìm thiết bị có tên **`Pi-Setup`** và nhấn **Connect**.
4. Vào tab **Client**, tìm mục có UUID `1234` và bấm vào để xổ xuống.
5. Bên trong sẽ thấy **Characteristic UUID `abcd`**. Nhấn vào biểu tượng **mũi tên chỉ lên** (tương đương lệnh **Write**).
6. Chọn kiểu dữ liệu gửi là **Text (UTF-8)**.
7. Nhập cấu hình WiFi dưới dạng **chuỗi JSON chính xác** (Lưu ý phải là ngoặc kép `""`):

   ```json
   { "ssid": "Ten_WiFi_Nha_Ban", "password": "Mat_Khau_WiFi" }
   ```

8. Nhấn **Send/Write**.
9. Board sẽ tiếp nhận lệnh và tự động bắt mạng wifi đó (BLE vẫn tiếp tục duy trì phòng khi bạn muốn đổi mạng khác).

### Cách 2: Sử dụng Python trên Máy Tính (Windows / Mac / Linux)

Nếu bạn muốn cấu hình bằng Laptop/PC, dùng script Python với thư viện `bleak`.

Mở terminal/cmd trên máy tính và cài đặt thư viện:

```bash
pip install bleak
```

Sau đó tạo file `ble_client.py` và chạy đoạn code sau:

```python
import asyncio
from bleak import BleakScanner, BleakClient

# Thay bằng tên WiFi và Mật khẩu thực tế của bạn
WIFI_DATA = '{"ssid":"Ten_WiFi_Nha_Ban","password":"Mat_Khau_WiFi"}'

async def main():
    print("🔍 Đang quét tìm thiết bị 'Pi-Setup'...")
    devices = await BleakScanner.discover()

    # Tìm thiết bị có tên là Pi-Setup
    pi_device = next((d for d in devices if d.name == 'Pi-Setup'), None)

    if not pi_device:
        print("❌ Không tìm thấy 'Pi-Setup'. Hãy chắc chắn mạch đang bật Bluetooth.")
        return

    print(f"✅ Đã tìm thấy Pi-Setup ({pi_device.address}). Đang kết nối...")

    async with BleakClient(pi_device.address) as client:
        print("🔗 Kết nối thành công! Đang gửi cấu hình WiFi...")

        # UUID 128-bit đầy đủ của Characteristic
        char_uuid = "0000abcd-0000-1000-8000-00805f9b34fb"

        # Gửi dữ liệu JSON
        await client.write_gatt_char(char_uuid, WIFI_DATA.encode('utf-8'))
        print("✅ Đã gửi cấu hình WiFi thành công! Mạch sẽ tự động kết nối.")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔍 Kiểm tra nhanh trước khi Scan

Nếu bạn muốn kiểm tra mạch đang phát BLE đúng chưa, SSH vào Pi và chạy:

```bash
# Xem log BLE server
sudo journalctl -u ble-setup -n 30 --no-pager

# Xem trạng thái Bluetooth adapter
hciconfig

# Quét BLE từ chính Pi (nếu cần debug)
sudo hcitool lescan
```

---

## ⚠️ Các Lỗi Thường Gặp & Cách Khắc Phục

❌ **Không quét thấy thiết bị "Pi-Setup" trên app**

- Kiểm tra Bluetooth đã bật trên mạch chưa:
  ```bash
  sudo hciconfig hci0 up
  ```
- Kiểm tra service đang chạy hay báo lỗi:
  ```bash
  sudo systemctl status ble-setup
  sudo journalctl -u ble-setup -n 50 --no-pager
  ```
- Nếu log báo `Lỗi đăng ký Advertisement`, thử khởi động lại Bluetooth:
  ```bash
  sudo systemctl restart bluetooth
  sudo systemctl restart ble-setup
  ```

❌ **Nhấn Write (gửi) báo lỗi hoặc mạch không có phản hồi**

- Chắc chắn gửi đúng chuỗi JSON với dấu ngoặc kép `""`. Sai cú pháp JSON thì code sẽ bắt lỗi và bỏ qua.
- Điện thoại phải được cấp quyền Bluetooth / Vị Trí đầy đủ cho ứng dụng nRF Connect.

❌ **Gửi thành công nhưng mạch vẫn không có WiFi**

- Có thể bạn gõ sai Tên WiFi (SSID) hoặc Mật Khẩu.
- Mạch không tìm thấy sóng WiFi đó. SSH vào mạch và chạy:
  ```bash
  sudo nmcli dev wifi
  ```
  để quét xem mạch có thực sự nhìn thấy SSID đó không.

❌ **Lỗi `No module named 'gi'` hoặc `No module named 'dbus'`**

- Cài đặt lại các gói hệ thống:
  ```bash
  sudo apt-get install -y python3-dbus python3-gi
  ```
