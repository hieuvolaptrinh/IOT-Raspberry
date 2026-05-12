# 📡 Hướng Dẫn Cấu Hình WiFi Từ Xa Bằng BLE

Tài liệu này hướng dẫn cách cấu hình và chạy file `ble_server.py` để board (VD: Raspberry Pi) luôn tự động phát sóng Bluetooth (BLE). Từ đó, bạn có thể dùng điện thoại kết nối vào board và cấu hình mạng WiFi bất cứ lúc nào.

---

## 🛠 BƯỚC 1 — Cài đặt các thư viện cần thiết trên mạch

Mã nguồn trong `ble_server.py` sử dụng thư viện `pybleno`. Trên board (Raspberry Pi/Linux), mở terminal và chạy các lệnh sau:

1. **Cài đặt thư viện xử lý Bluetooth cho hệ điều hành:**
   ```bash
   sudo apt-get update
   sudo apt-get install bluetooth bluez libbluetooth-dev libudev-dev
   ```

2. **Cài đặt thư viện Python (`pybleno`):**
   ```bash
   pip install pybleno
   ```

3. **Đảm bảo `NetworkManager` (nmcli) có sẵn để kết nối WiFi:**
   (Thường đã có sẵn trên các bản Raspberry Pi OS mới, nếu chưa thì chạy lệnh sau)
   ```bash
   sudo apt-get install network-manager
   ```

---

## 💻 BƯỚC 2 — Cách hoạt động của `ble_server.py`

Mã nguồn `ble_server.py` đã được cung cấp sẵn. Quy trình hoạt động của nó như sau:
1. **Khởi động**: Khi chạy, script sẽ luôn bật BLE Server với tên hiển thị là **`Pi-Setup`**.
2. **Lắng nghe BLE**: Đợi tín hiệu ở Service UUID `1234` và Characteristic UUID `abcd`.
3. **Nhận Cấu Hình**: Chờ nhận dữ liệu dạng JSON: `{"ssid":"Tên_WiFi","password":"Mật_khẩu"}`.
4. **Thực thi**: Khi nhận đúng dữ liệu, nó sẽ gọi hệ thống (`nmcli`) để lưu cấu hình và kết nối mạch vào WiFi mới mà không làm tắt Bluetooth.

---

## 🚀 BƯỚC 3 — Cho BLE tự chạy khi khởi động

Để mạch luôn tự động phát BLE mỗi khi cắm điện, chúng ta thiết lập dưới dạng Systemd service.

1. **Tạo service mới:**
   ```bash
   sudo nano /etc/systemd/system/ble-setup.service
   ```

2. **Dán nội dung sau vào file:** *(Lưu ý: Đổi đường dẫn tuyệt đối cho chuẩn xác với vị trí file `ble_server.py` trên mạch của bạn, thay vì `/đường_dẫn_của_bạn/`)*
   ```ini
   [Unit]
   Description=BLE WiFi Setup Service
   After=network.target bluetooth.target

   [Service]
   # Thay bằng đường dẫn tuyệt đối đến python và file ble_server.py
   ExecStart=/usr/bin/python3 /đường_dẫn_của_bạn/ble_server.py
   Restart=always
   User=root

   [Install]
   WantedBy=multi-user.target
   ```

3. **Lưu file (Ctrl+O, Enter, Ctrl+X) và Bật service khởi động cùng hệ thống:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ble-setup
   sudo systemctl start ble-setup
   ```

👉 **Từ giờ:** Mỗi lần khởi động, Bluetooth sẽ luôn được phát để bạn có thể vào điều chỉnh mạng bất cứ lúc nào.

---

## 📱 BƯỚC 4 — Cách kết nối và thiết lập WiFi từ Điện Thoại

Bất cứ lúc nào muốn kết nối mạch vào WiFi mới, bạn có thể dùng điện thoại (Android/iOS) để thực hiện.

### Cách Dễ Nhất: Dùng ứng dụng nRF Connect
1. Tải app **nRF Connect for Mobile** trên CH Play hoặc App Store.
2. Bật Bluetooth trên điện thoại, mở app **nRF Connect** và nhấn nút **Scan**.
3. Tìm thiết bị có tên **`Pi-Setup`** và nhấn **Connect**.
4. Vào tab **Client**, tìm mục có UUID `1234` và bấm vào để xổ xuống.
5. Bên trong sẽ thấy **Characteristic UUID `abcd`**. Nhấn vào biểu tượng **mũi tên chỉ lên** (tương đương lệnh **Write**).
6. Chọn kiểu dữ liệu gửi là **Text (UTF-8)**.
7. Nhập cấu hình WiFi dưới dạng **chuỗi JSON chính xác** (Lưu ý phải là ngoặc kép `""`):
   ```json
   {"ssid":"Ten_WiFi_Nha_Ban", "password":"Mat_Khau_WiFi"}
   ```
8. Nhấn **Send/Write**.
9. Board sẽ tiếp nhận lệnh và tự động bắt mạng wifi đó (BLE vẫn tiếp tục duy trì phòng khi bạn muốn đổi mạng khác).

---

## ⚠️ Các Lỗi Thường Gặp & Cách Khắc Phục

❌ **Không quét thấy thiết bị "Pi-Setup" trên app**
- Kiểm tra lại bluetooth đã được bật hoàn toàn trên mạch chưa bằng cách gõ:
  `sudo hciconfig hci0 up`
- Kiểm tra service python có đang bị báo lỗi không:
  `sudo systemctl status ble-setup`

❌ **Nhấn Write (gửi) báo lỗi hoặc mạch không có phản hồi**
- Chắc chắn bạn đã gửi đúng chuỗi JSON với dấu ngoặc kép `""`. Sai cú pháp JSON thì code sẽ bắt lỗi và bỏ qua.
- Điện thoại phải được cấp quyền Bluetooth / Vị Trí đầy đủ cho ứng dụng nRF Connect.

❌ **Gửi thành công nhưng mạch vẫn không có WiFi**
- Có thể bạn gõ sai Tên WiFi (SSID) hoặc Mật Khẩu. 
- Mạch không tìm thấy sóng WiFi đó. Bạn có thể SSH vào mạch (nếu cắm cáp LAN) và chạy `sudo nmcli dev wifi` để quét xem mạch có thực sự nhìn thấy SSID đó không.
