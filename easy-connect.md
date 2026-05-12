# 🌐 Hướng Dẫn Kết Nối & Quản Lý Mạch Từ Xa

Tài liệu này hướng dẫn cách truy cập mạch Raspberry Pi từ **bất kỳ đâu** (không cần cùng WiFi), và cách sử dụng BLE để cấu hình mạch **không cần SSH**.

---

## Tổng quan: 3 bước để kết nối mạch từ mọi nơi

```
┌─────────────────┐     BLE      ┌────────────────┐    Tailscale    ┌──────────────┐
│  📱 Điện thoại   │ ──────────→ │  🔧 Raspberry  │ ←────────────→ │  💻 Máy tính  │
│  (nRF Connect)  │  WiFi config │     Pi         │   SSH từ xa    │  (bất kỳ đâu)│
└─────────────────┘              └────────────────┘                └──────────────┘
```

1. **BLE** → Cấu hình WiFi + API_URL + Xem IP (không cần mạng)
2. **Tailscale** → Truy cập SSH từ bất kỳ đâu trên thế giới
3. **SSH** → Quản lý, sửa code, restart service

---

## 📡 PHẦN 1 — Cấu hình mạch qua BLE (Không cần mạng)

BLE Server trên mạch cung cấp 2 tính năng chính:

| Tính năng | UUID | Loại | Mô tả |
|---|---|---|---|
| Cấu hình WiFi + API | `abcd` | Write | Gửi JSON để kết nối WiFi và cập nhật `.env` |
| Xem IP mạch | `abce` | Read | Đọc IP WiFi, Tailscale, hostname |

### 1.1 Gửi cấu hình WiFi + API_URL (Write UUID `abcd`)

Mở app **nRF Connect** trên điện thoại → Scan → Tìm **`Pi-Setup`** → Connect:

**Chỉ cấu hình WiFi:**
```json
{"ssid":"Ten_WiFi","password":"Mat_Khau"}
```

**Cấu hình WiFi + API_URL cùng lúc:**
```json
{"ssid":"Ten_WiFi","password":"Mat_Khau","api_url":"http://192.168.1.100:8000"}
```

**Chỉ đổi API_URL (khi mạch đã có WiFi):**
```json
{"api_url":"http://100.64.0.5:8000"}
```

> ✅ Khi gửi `api_url`, mạch sẽ tự động cập nhật file `.env` và restart service chính.

### 1.2 Đọc IP hiện tại của mạch (Read UUID `abce`)

Trong app nRF Connect, sau khi Connect vào `Pi-Setup`:

1. Tìm Characteristic có UUID `abce`
2. Nhấn **mũi tên chỉ xuống** (Read)
3. Mạch sẽ trả về JSON dạng:
   ```json
   {"wifi":"192.168.1.50","tailscale":"100.64.0.3","hostname":"hieuvo"}
   ```

Từ đây bạn biết được IP để SSH hoặc truy cập API.

### 1.3 Đọc IP bằng Python trên máy tính

```python
import asyncio
from bleak import BleakScanner, BleakClient

async def read_ip():
    print("🔍 Đang quét tìm Pi-Setup...")
    devices = await BleakScanner.discover()
    pi = next((d for d in devices if d.name == 'Pi-Setup'), None)

    if not pi:
        print("❌ Không tìm thấy Pi-Setup")
        return

    async with BleakClient(pi.address) as client:
        # Đọc IP từ Characteristic UUID abce
        ip_uuid = "0000abce-0000-1000-8000-00805f9b34fb"
        data = await client.read_gatt_char(ip_uuid)
        print(f"🌐 IP mạch: {data.decode('utf-8')}")

asyncio.run(read_ip())
```

---

## 🌍 PHẦN 2 — Cài Tailscale để truy cập mạch từ mọi nơi

Tailscale tạo một mạng VPN riêng (miễn phí), cho phép bạn SSH vào mạch từ bất kỳ đâu — quán café, trường học, nhà bạn — chỉ cần có internet.

### 2.1 Cài đặt trên Raspberry Pi

SSH vào Pi (hoặc dùng terminal trực tiếp) và chạy:

```bash
# Cài Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Kích hoạt (sẽ hiển thị link đăng nhập)
sudo tailscale up
```

Terminal sẽ hiện một link dạng `https://login.tailscale.com/a/xxxx`.
Mở link đó trên trình duyệt → Đăng nhập bằng Google/GitHub → Xác nhận thiết bị.

### 2.2 Cài đặt trên Máy tính / Điện thoại

| Thiết bị | Cách cài |
|---|---|
| **Windows** | Tải tại [tailscale.com/download](https://tailscale.com/download) |
| **Mac** | Tải trên App Store hoặc `brew install tailscale` |
| **Android** | Tải trên CH Play: "Tailscale" |
| **iOS** | Tải trên App Store: "Tailscale" |

Đăng nhập cùng tài khoản Google/GitHub với Pi.

### 2.3 Xem IP Tailscale

Sau khi cài xong, mỗi thiết bị sẽ có một **IP cố định** dạng `100.x.x.x`.

**Trên Pi:**
```bash
tailscale ip -4
# Ví dụ: 100.64.0.3
```

**Trên máy tính:**
```bash
tailscale ip -4
# Ví dụ: 100.64.0.5
```

Hoặc vào trang [login.tailscale.com](https://login.tailscale.com) để xem tất cả thiết bị và IP.

### 2.4 Cho Tailscale tự chạy khi khởi động (trên Pi)

```bash
sudo systemctl enable tailscaled
```

---

## 💻 PHẦN 3 — SSH vào mạch từ bất kỳ đâu

Sau khi cả Pi và máy tính đều cài Tailscale:

```bash
# SSH bằng IP Tailscale (hoạt động ở mọi nơi)
ssh pi@100.64.0.3

# Hoặc bằng hostname (nếu Tailscale đã đồng bộ DNS)
ssh pi@hieuvo
```

### 3.1 Sửa file .env qua SSH

```bash
nano /home/pi/IOT-Raspberry/.env
```

Sửa `API_URL` rồi restart service:

```bash
sudo systemctl restart signify
```

### 3.2 Xem log service

```bash
# Log BLE server
sudo journalctl -u ble-setup -f

# Log service chính
sudo journalctl -u signify -f
```

---

## 📋 PHẦN 4 — Quy trình Setup mạch mới từ đầu

Khi bạn mang mạch đến một nơi mới (WiFi khác), đây là quy trình nhanh nhất:

### Bước 1: Cấp WiFi qua BLE
1. Mở app **nRF Connect** trên điện thoại
2. Scan → Tìm **Pi-Setup** → Connect
3. Write vào UUID `abcd`:
   ```json
   {"ssid":"WiFi_Moi","password":"MatKhau123","api_url":"http://100.64.0.5:8000"}
   ```
4. Mạch tự động kết nối WiFi + cập nhật API_URL

### Bước 2: Xác nhận IP
1. Read UUID `abce` để xem IP mới
2. Hoặc dùng Tailscale IP (cố định, không đổi khi chuyển WiFi)

### Bước 3: SSH vào kiểm tra (nếu cần)
```bash
ssh pi@100.64.0.3
sudo systemctl status signify
```

> 💡 **Mẹo:** Vì Tailscale IP là cố định (`100.x.x.x`), bạn nên set `API_URL` trong `.env` bằng IP Tailscale của server backend. Như vậy dù mạch đổi WiFi thì API_URL vẫn không thay đổi!

---

## ⚠️ Xử lý sự cố

| Vấn đề | Giải pháp |
|---|---|
| Không quét thấy Pi-Setup | `sudo hciconfig hci0 up && sudo systemctl restart ble-setup` |
| Tailscale không kết nối | `sudo tailscale up --reset` |
| SSH timeout | Kiểm tra cả 2 thiết bị đã cài Tailscale và cùng tài khoản chưa |
| Mạch mất WiFi sau khi reboot | BLE sẽ tự phát, dùng điện thoại cấp lại WiFi |
| Muốn đổi API_URL mà không có mạng | Gửi qua BLE: `{"api_url":"http://..."}` |
