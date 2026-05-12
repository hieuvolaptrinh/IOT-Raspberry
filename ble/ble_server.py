#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import json
import os
import subprocess
import sys

from gi.repository import GLib

# ============ BLUEZ D-BUS INTERFACES ============
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

# ============ UUIDs ============
WIFI_SERVICE_UUID = '00001234-0000-1000-8000-00805f9b34fb'
WIFI_CHRC_UUID = '0000abcd-0000-1000-8000-00805f9b34fb'   # Write: WiFi + ENV config
IP_CHRC_UUID = '0000abce-0000-1000-8000-00805f9b34fb'     # Read:  IP info

# ============ ĐƯỜNG DẪN .ENV ============
# Thay đổi nếu project của bạn nằm ở đường dẫn khác
ENV_FILE_PATH = '/home/pi/IOT-Raspberry/.env'

# ============ HELPER FUNCTIONS ============
def get_device_ips():
    """Lấy tất cả IP hiện tại của mạch (WiFi, Tailscale, Ethernet...)."""
    ips = {}
    try:
        result = subprocess.run(
            ['hostname', '-I'], capture_output=True, text=True, timeout=5
        )
        all_ips = result.stdout.strip().split()
        for ip in all_ips:
            if ip.startswith('100.'):
                ips['tailscale'] = ip
            elif ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                ips['wifi'] = ip
    except Exception:
        pass

    # Lấy hostname
    try:
        result = subprocess.run(
            ['hostname'], capture_output=True, text=True, timeout=5
        )
        ips['hostname'] = result.stdout.strip()
    except Exception:
        pass

    return ips


def connect_wifi(ssid, password):
    """Kết nối WiFi bằng nmcli."""
    print(f"📶 Đang kết nối WiFi: {ssid}...")
    try:
        result = subprocess.run(
            ['sudo', 'nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"✅ Kết nối WiFi '{ssid}' thành công!")
        else:
            print(f"❌ Kết nối WiFi thất bại: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("❌ Kết nối WiFi bị timeout (quá 30 giây).")
    except Exception as e:
        print(f"❌ Lỗi kết nối WiFi: {e}")


def update_env_file(api_url):
    """Cập nhật API_URL trong file .env"""
    print(f"📝 Đang cập nhật .env: API_URL={api_url}")
    try:
        # Đọc file .env hiện tại
        env_lines = []
        found = False
        if os.path.exists(ENV_FILE_PATH):
            with open(ENV_FILE_PATH, 'r') as f:
                for line in f:
                    if line.strip().startswith('API_URL='):
                        env_lines.append(f'API_URL={api_url}\n')
                        found = True
                    else:
                        env_lines.append(line)

        if not found:
            env_lines.append(f'API_URL={api_url}\n')

        # Ghi lại file
        with open(ENV_FILE_PATH, 'w') as f:
            f.writelines(env_lines)

        print(f"✅ Đã cập nhật .env thành công!")

        # Restart service chính (real_time.py) để nhận config mới
        try:
            subprocess.run(
                ['sudo', 'systemctl', 'restart', 'signify'],
                capture_output=True, timeout=10
            )
            print("🔄 Đã restart service chính (signify)")
        except Exception:
            print("⚠️ Không tìm thấy service 'signify' để restart (bỏ qua)")

    except Exception as e:
        print(f"❌ Lỗi cập nhật .env: {e}")


# ============ BLUEZ HELPERS ============
def find_adapter(bus):
    """Tìm adapter Bluetooth (hci0) trên hệ thống."""
    remote_om = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, '/'),
        DBUS_OM_IFACE
    )
    objects = remote_om.GetManagedObjects()
    for path, interfaces in objects.items():
        if GATT_MANAGER_IFACE in interfaces:
            return path
    return None


# ============ BLE ADVERTISEMENT ============
class Advertisement(dbus.service.Object):
    """Quảng bá BLE để điện thoại/máy tính có thể quét thấy."""

    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = 'peripheral'
        self.local_name = 'Pi-Setup'
        self.service_uuids = [WIFI_SERVICE_UUID]
        self.include_tx_power = True
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            LE_ADVERTISEMENT_IFACE: {
                'Type': self.ad_type,
                'LocalName': dbus.String(self.local_name),
                'ServiceUUIDs': dbus.Array(self.service_uuids, signature='s'),
                'IncludeTxPower': dbus.Boolean(self.include_tx_power),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs',
                'Invalid interface: ' + interface
            )
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        print("📡 Advertisement released")


# ============ GATT SERVICE ============
class WifiService(dbus.service.Object):
    """GATT Service chứa các Characteristic."""

    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = WIFI_SERVICE_UUID
        self.primary = True
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    [c.get_path() for c in self.characteristics],
                    signature='o'
                )
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs',
                'Invalid interface: ' + interface
            )
        return self.get_properties()[GATT_SERVICE_IFACE]


# ============ CHARACTERISTIC 1: WiFi + ENV Config (UUID abcd - Write) ============
class WifiCharacteristic(dbus.service.Object):
    """
    UUID abcd — Nhận cấu hình WiFi + API_URL từ điện thoại/máy tính.

    Dữ liệu gửi vào (JSON):
      {"ssid":"TenWifi", "password":"MatKhau"}
      {"ssid":"TenWifi", "password":"MatKhau", "api_url":"http://x.x.x.x:8000"}
    """

    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = WIFI_CHRC_UUID
        self.service = service
        self.flags = ['write']
        self.value = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Value': dbus.Array(self.value, signature='y'),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs',
                'Invalid interface: ' + interface
            )
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        """Nhận dữ liệu WiFi + API_URL từ client."""
        try:
            raw_bytes = bytes([int(b) for b in value])
            decoded = raw_bytes.decode('utf-8')
            print(f"📥 Nhận được dữ liệu: {decoded}")

            wifi_info = json.loads(decoded)
            ssid = wifi_info.get("ssid", "").strip()
            password = wifi_info.get("password", "").strip()
            api_url = wifi_info.get("api_url", "").strip()

            # Kết nối WiFi nếu có SSID + Password
            if ssid and password:
                print(f"🔑 SSID: {ssid} | Password: {'*' * len(password)}")
                GLib.timeout_add(100, lambda: connect_wifi(ssid, password) or False)

            # Cập nhật .env nếu có api_url
            if api_url:
                GLib.timeout_add(2000, lambda: update_env_file(api_url) or False)

            if not ssid and not api_url:
                print("⚠️ JSON không chứa ssid hoặc api_url, bỏ qua.")

        except json.JSONDecodeError as e:
            print(f"❌ Lỗi parse JSON: {e}")
        except Exception as e:
            print(f"❌ Lỗi xử lý dữ liệu: {e}")


# ============ CHARACTERISTIC 2: IP Info (UUID abce - Read) ============
class IPInfoCharacteristic(dbus.service.Object):
    """
    UUID abce — Đọc thông tin IP hiện tại của mạch.

    Khi client đọc (Read), trả về JSON chứa:
      {"wifi":"192.168.1.50","tailscale":"100.x.x.x","hostname":"hieuvo"}
    """

    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = IP_CHRC_UUID
        self.service = service
        self.flags = ['read']
        self.value = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Value': dbus.Array(self.value, signature='y'),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs',
                'Invalid interface: ' + interface
            )
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        """Trả về JSON chứa IP hiện tại của mạch."""
        ips = get_device_ips()
        ip_json = json.dumps(ips, ensure_ascii=False)
        print(f"📤 Client đọc IP: {ip_json}")
        return dbus.Array([dbus.Byte(b) for b in ip_json.encode('utf-8')], signature='y')


# ============ APPLICATION ============
class WifiSetupApplication(dbus.service.Object):
    """
    GATT Application — đăng ký tất cả Service và Characteristic với BlueZ.
    """

    def __init__(self, bus):
        self.path = '/org/bluez/example'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

        # Tạo WiFi Service
        wifi_service = WifiService(bus, 0)

        # Characteristic 1: WiFi + ENV config (Write) — UUID abcd
        wifi_chrc = WifiCharacteristic(bus, 0, wifi_service)
        wifi_service.characteristics.append(wifi_chrc)

        # Characteristic 2: IP Info (Read) — UUID abce
        ip_chrc = IPInfoCharacteristic(bus, 1, wifi_service)
        wifi_service.characteristics.append(ip_chrc)

        self.services.append(wifi_service)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        """Trả về tất cả objects cho BlueZ đăng ký."""
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for chrc in service.characteristics:
                response[chrc.get_path()] = chrc.get_properties()
        return response


# ============ CALLBACKS ============
def register_ad_cb():
    print("✅ Đang phát sóng BLE (Advertising) thành công!")
    print("📱 Mở app nRF Connect → Scan → Tìm 'Pi-Setup'")

def register_ad_error_cb(error):
    print(f"❌ Lỗi đăng ký Advertisement: {error}")
    mainloop.quit()

def register_app_cb():
    print("✅ GATT Application đã đăng ký thành công!")
    ips = get_device_ips()
    if ips:
        print(f"🌐 IP hiện tại: {json.dumps(ips)}")

def register_app_error_cb(error):
    print(f"❌ Lỗi đăng ký GATT Application: {error}")
    mainloop.quit()


# ============ MAIN ============
if __name__ == '__main__':
    print("=" * 50)
    print("📡 BLE WiFi Setup Server v2.0")
    print("   BlueZ D-Bus API (có sẵn trên RPi OS)")
    print("   Characteristics:")
    print("     UUID abcd → Write WiFi + API_URL config")
    print("     UUID abce → Read IP hiện tại")
    print("=" * 50)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter_path = find_adapter(bus)
    if not adapter_path:
        print("❌ Không tìm thấy Bluetooth adapter!")
        print("   Thử chạy: sudo hciconfig hci0 up")
        sys.exit(1)

    print(f"🔵 Bluetooth adapter: {adapter_path}")

    # Bật Bluetooth adapter
    adapter_props = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        DBUS_PROP_IFACE
    )
    try:
        adapter_props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(True))
        print("🔵 Bluetooth adapter đã được bật")
    except Exception as e:
        print(f"⚠️ Không thể bật adapter (có thể đã bật): {e}")

    # Tạo GATT Application
    app = WifiSetupApplication(bus)

    # Tạo BLE Advertisement
    adv = Advertisement(bus, 0)

    # Đăng ký Advertisement
    ad_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        LE_ADVERTISING_MANAGER_IFACE
    )
    ad_manager.RegisterAdvertisement(
        adv.get_path(), {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb
    )

    # Đăng ký GATT Application
    gatt_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        GATT_MANAGER_IFACE
    )
    gatt_manager.RegisterApplication(
        app.get_path(), {},
        reply_handler=register_app_cb,
        error_handler=register_app_error_cb
    )

    print("BLE Server đang chạy (Luôn phát sóng)...")
    print("   Nhấn Ctrl+C để tắt.\n")

    mainloop = GLib.MainLoop()
    try:
        mainloop.run()
    except KeyboardInterrupt:
        print("\nĐang tắt BLE Server...")
        ad_manager.UnregisterAdvertisement(adv.get_path())
        print("👋 Đã tắt.")