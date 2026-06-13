# 📡 Hướng Dẫn Cấu Hình WiFi Từ Xa Bằng BLE

Tài liệu này hướng dẫn cách cấu hình và chạy file `ble_server.py` để board (Raspberry Pi) luôn tự động phát sóng Bluetooth (BLE). Từ đó, bạn có thể dùng điện thoại hoặc máy tính kết nối vào board và cấu hình mạng WiFi, API_URL, hoặc xem IP mạch bất cứ lúc nào.

> **Lưu ý:** Code sử dụng **BlueZ D-Bus API** — thư viện có sẵn trên Raspberry Pi OS, **không cần `pip install` thêm bất kỳ thư viện bên ngoài nào**.

---

## 🛠 BƯỚC 1 — Cài đặt các gói cần thiết trên mạch

Mở terminal trên Raspberry Pi và chạy các lệnh sau:

```bash
sudo apt-get update
sudo apt-get install -y bluetooth bluez python3-dbus python3-gi network-manager
```

Sau đó **mở khóa Bluetooth** và bật adapter:

```bash
sudo rfkill unblock bluetooth
sudo hciconfig hci0 up
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
```

> ✅ **Không cần `pip install` gì cả!** Tất cả thư viện Python (`dbus`, `gi`) đều đi kèm với Raspberry Pi OS.

---

## 💻 BƯỚC 2 — Cách hoạt động của `ble_server.py`

Mã nguồn `ble_server.py` sử dụng BlueZ D-Bus API (cách chính thức của Linux). BLE Server cung cấp 2 tính năng:

| Tính năng           | UUID   | Loại  | Mô tả                                       |
| ------------------- | ------ | ----- | ------------------------------------------- |
| Cấu hình WiFi + API | `abcd` | Write | Gửi JSON để kết nối WiFi và cập nhật `.env` |
| Xem IP mạch         | `abce` | Read  | Đọc IP WiFi, Tailscale, hostname            |

Quy trình hoạt động:

1. **Khởi động**: Script đăng ký GATT Service và BLE Advertisement với BlueZ.
2. **Phát sóng**: Bluetooth luôn phát sóng với tên hiển thị **`Pi-Setup`**.
3. **Nhận cấu hình** (UUID `abcd`): Chờ nhận JSON từ điện thoại/máy tính:
   - `{"ssid":"TenWifi","password":"MatKhau"}` → Kết nối WiFi
   - `{"ssid":"TenWifi","password":"MatKhau","api_url":"http://x.x.x.x:8000"}` → WiFi + cập nhật `.env`
   - `{"api_url":"http://x.x.x.x:8000"}` → Chỉ đổi API_URL
4. **Trả IP** (UUID `abce`): Khi client đọc, trả về JSON: `{"wifi":"192.168.1.50","hostname":"hieuvo"}`

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
   ExecStartPre=/usr/bin/rfkill unblock bluetooth
   ExecStartPre=/bin/sleep 1
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

   ```bash
   sudo systemctl status ble-setup
   ```

   Nếu thấy dòng `Active: active (running)` là đã thành công ✅

👉 **Từ giờ:** Mỗi lần khởi động, Bluetooth sẽ tự mở khóa và phát sóng để bạn có thể vào điều chỉnh mạng bất cứ lúc nào.

---

## 📱 BƯỚC 4 — Cách kết nối và thiết lập WiFi

Bất cứ lúc nào muốn kết nối mạch vào WiFi mới, bạn có thể dùng **điện thoại** hoặc **máy tính**.

### Cách 1: Dùng ứng dụng nRF Connect (Điện thoại)

1. Tải app **nRF Connect for Mobile** trên CH Play hoặc App Store.
2. Bật Bluetooth trên điện thoại, mở app **nRF Connect** và nhấn nút **Scan**.
3. Tìm thiết bị có tên **`Pi-Setup`** và nhấn **Connect**.
4. Vào tab **Client**, tìm mục có UUID `1234` và bấm vào để xổ xuống.

**Gửi cấu hình WiFi (Write UUID `abcd`):**

5. Tìm **Characteristic UUID `abcd`**, nhấn vào biểu tượng **mũi tên chỉ lên** (Write).
6. Chọn kiểu dữ liệu gửi là **Text (UTF-8)**.
7. Nhập cấu hình WiFi dưới dạng JSON:

   ```json
   { "ssid": "Ten_WiFi", "password": "Mat_Khau" }
   ```

   Hoặc gửi kèm API_URL:

   ```json
   {
     "ssid": "Ten_WiFi",
     "password": "Mat_Khau",
     "api_url": "http://192.168.1.100:8000"
   }
   ```

8. Nhấn **Send/Write**.

**Đọc IP mạch (Read UUID `abce`):**

9. Tìm **Characteristic UUID `abce`**, nhấn vào biểu tượng **mũi tên chỉ xuống** (Read).
10. Mạch sẽ trả về JSON chứa IP hiện tại:

    ```json
    { "wifi": "192.168.1.50", "tailscale": "100.64.0.3", "hostname": "hieuvo" }
    ```

    > 💡 **Tip kết nối từ xa (Mọi IP bên ngoài):** 
    > Sử dụng IP của `tailscale` (VD: `100.64.0.3`) để kết nối SSH tới mạch từ BẤT KỲ ĐÂU trên thế giới (kể cả dùng 4G), miễn là máy tính của bạn cũng đang cài đặt và bật Tailscale!
    > Lệnh kết nối: `ssh TÊN_USER_CỦA_BẠN@100.64.0.3`

### Cách 2: Sử dụng Python trên Máy Tính (Windows / Mac / Linux)

Mở terminal/cmd trên máy tính và cài đặt thư viện:

```bash
pip install bleak
```

Sau đó tạo file `ble_client.py` và chạy đoạn code sau:

```python
import asyncio
from bleak import BleakScanner, BleakClient

WIFI_CHRC = "0000abcd-0000-1000-8000-00805f9b34fb"  # Write: WiFi config
IP_CHRC = "0000abce-0000-1000-8000-00805f9b34fb"    # Read: IP info

async def main():
    print("🔍 Đang quét tìm thiết bị 'Pi-Setup'...")
    devices = await BleakScanner.discover()
    pi_device = next((d for d in devices if d.name == 'Pi-Setup'), None)

    if not pi_device:
        print("❌ Không tìm thấy 'Pi-Setup'.")
        return

    print(f"✅ Đã tìm thấy Pi-Setup ({pi_device.address}). Đang kết nối...")

    async with BleakClient(pi_device.address) as client:
        # --- Đọc IP mạch ---
        ip_data = await client.read_gatt_char(IP_CHRC)
        print(f"🌐 IP mạch: {ip_data.decode('utf-8')}")

        # --- Gửi cấu hình WiFi ---
        wifi_data = '{"ssid":"Ten_WiFi","password":"Mat_Khau"}'
        await client.write_gatt_char(WIFI_CHRC, wifi_data.encode('utf-8'))
        print("✅ Đã gửi cấu hình WiFi thành công!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔍 Kiểm tra nhanh & Debug

```bash
# Xem log BLE server
sudo journalctl -u ble-setup -n 30 --no-pager

# Xem trạng thái Bluetooth adapter
hciconfig

# Kiểm tra Bluetooth có bị khóa không
sudo rfkill list

# Quét BLE từ chính Pi (nếu cần debug)
sudo hcitool lescan
```

---

## ⚠️ Các Lỗi Thường Gặp & Cách Khắc Phục

❌ **Bluetooth bị Soft blocked (rfkill)**

- Đây là lỗi phổ biến nhất. Chạy:
  ```bash
  sudo rfkill unblock bluetooth
  sudo hciconfig hci0 up
  sudo systemctl restart bluetooth
  sudo systemctl restart ble-setup
  ```

❌ **Không quét thấy thiết bị "Pi-Setup" trên app**

- Kiểm tra service đang chạy:
  ```bash
  sudo systemctl status ble-setup
  sudo journalctl -u ble-setup -n 20 --no-pager
  ```

❌ **Lỗi `No module named 'dbus'` hoặc `No module named 'gi'`**

- Cài đặt lại:
  ```bash
  sudo apt-get install -y python3-dbus python3-gi
  ```

❌ **Lỗi `org.bluez was not provided by any .service files`**

- BlueZ chưa chạy:
  ```bash
  sudo apt-get install -y bluetooth bluez
  sudo systemctl start bluetooth
  ```

❌ **Lỗi `Failed to register advertisement`**

- Bluetooth adapter chưa được mở khóa hoặc chưa bật:
  ```bash
  sudo rfkill unblock bluetooth
  sudo hciconfig hci0 up
  sudo systemctl restart bluetooth
  sleep 2
  sudo systemctl restart ble-setup
  ```

❌ **Gửi thành công nhưng mạch vẫn không có WiFi**

- Có thể bạn gõ sai Tên WiFi (SSID) hoặc Mật Khẩu.
- Kiểm tra mạch có nhìn thấy WiFi đó không:
  ```bash
  sudo nmcli dev wifi
  ```
