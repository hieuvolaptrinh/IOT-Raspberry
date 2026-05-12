#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLE WiFi Setup Server - Sử dụng BlueZ D-Bus API (có sẵn trên Raspberry Pi OS)

Phát sóng BLE với tên "Pi-Setup", nhận cấu hình WiFi qua JSON.
Không cần pip install thêm thư viện nào - tất cả đều có sẵn trên hệ thống.
"""

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import json
import os
import subprocess
import array
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
WIFI_CHRC_UUID = '0000abcd-0000-1000-8000-00805f9b34fb'

# ============ WIFI CONNECTION ============
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
        properties = {
            LE_ADVERTISEMENT_IFACE: {
                'Type': self.ad_type,
                'LocalName': dbus.String(self.local_name),
                'ServiceUUIDs': dbus.Array(self.service_uuids, signature='s'),
                'IncludeTxPower': dbus.Boolean(self.include_tx_power),
            }
        }
        return properties

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
    """GATT Service chứa Characteristic để nhận cấu hình WiFi."""

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


# ============ GATT CHARACTERISTIC (nhận WiFi config) ============
class WifiCharacteristic(dbus.service.Object):
    """
    Characteristic UUID abcd — nhận dữ liệu JSON WiFi từ điện thoại/máy tính.
    Hỗ trợ: write (ghi dữ liệu) + read (đọc trạng thái hiện tại).
    """

    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = WIFI_CHRC_UUID
        self.service = service
        self.flags = ['write', 'read']
        self.value = []
        self.status_message = "Sẵn sàng nhận WiFi config"
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
        """Trả về trạng thái hiện tại khi client đọc."""
        msg = self.status_message.encode('utf-8')
        return dbus.Array([dbus.Byte(b) for b in msg], signature='y')

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        """Nhận dữ liệu WiFi JSON từ client và thực hiện kết nối."""
        try:
            # Chuyển đổi dbus.Array[Byte] → string
            raw_bytes = bytes([int(b) for b in value])
            decoded = raw_bytes.decode('utf-8')
            print(f"📥 Nhận được dữ liệu: {decoded}")

            # Parse JSON
            wifi_info = json.loads(decoded)
            ssid = wifi_info.get("ssid", "").strip()
            password = wifi_info.get("password", "").strip()

            if ssid and password:
                self.status_message = f"Đang kết nối: {ssid}"
                print(f"🔑 SSID: {ssid} | Password: {'*' * len(password)}")
                # Thực hiện kết nối WiFi (chạy trong thread riêng để không block BLE)
                GLib.timeout_add(100, lambda: connect_wifi(ssid, password) or False)
            else:
                self.status_message = "Lỗi: Thiếu SSID hoặc Password"
                print("❌ Thiếu SSID hoặc Password trong JSON!")

        except json.JSONDecodeError as e:
            self.status_message = "Lỗi: JSON không hợp lệ"
            print(f"❌ Lỗi parse JSON: {e}")
        except Exception as e:
            self.status_message = f"Lỗi: {str(e)[:30]}"
            print(f"❌ Lỗi xử lý dữ liệu: {e}")


# ============ APPLICATION ============
class WifiSetupApplication(dbus.service.Object):
    """
    GATT Application — đăng ký tất cả Service và Characteristic với BlueZ.
    BlueZ yêu cầu một Application object quản lý tập trung tất cả GATT objects.
    """

    def __init__(self, bus):
        self.path = '/org/bluez/example'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

        # Tạo WiFi Service + Characteristic
        wifi_service = WifiService(bus, 0)
        wifi_chrc = WifiCharacteristic(bus, 0, wifi_service)
        wifi_service.characteristics.append(wifi_chrc)
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

def register_app_error_cb(error):
    print(f"❌ Lỗi đăng ký GATT Application: {error}")
    mainloop.quit()


# ============ MAIN ============
if __name__ == '__main__':
    print("=" * 50)
    print("📡 BLE WiFi Setup Server")
    print("   Sử dụng BlueZ D-Bus API (có sẵn trên RPi OS)")
    print("=" * 50)

    # Khởi tạo D-Bus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # Tìm Bluetooth adapter
    adapter_path = find_adapter(bus)
    if not adapter_path:
        print("❌ Không tìm thấy Bluetooth adapter!")
        print("   Thử chạy: sudo hciconfig hci0 up")
        sys.exit(1)

    print(f"🔵 Bluetooth adapter: {adapter_path}")

    # Bật Bluetooth adapter nếu đang tắt
    adapter_props = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        DBUS_PROP_IFACE
    )
    try:
        adapter_props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(True))
        print("🔵 Bluetooth adapter đã được bật")
    except Exception as e:
        print(f"⚠️ Không thể bật adapter (có thể đã bật): {e}")

    # Tạo GATT Application (Service + Characteristic)
    app = WifiSetupApplication(bus)

    # Tạo BLE Advertisement
    adv = Advertisement(bus, 0)

    # Đăng ký Advertisement với BlueZ
    ad_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        LE_ADVERTISING_MANAGER_IFACE
    )
    ad_manager.RegisterAdvertisement(
        adv.get_path(), {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb
    )

    # Đăng ký GATT Application với BlueZ
    gatt_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        GATT_MANAGER_IFACE
    )
    gatt_manager.RegisterApplication(
        app.get_path(), {},
        reply_handler=register_app_cb,
        error_handler=register_app_error_cb
    )

    print("🔴 BLE Server đang chạy (Luôn phát sóng)...")
    print("   Nhấn Ctrl+C để tắt.\n")

    # Chạy mainloop
    mainloop = GLib.MainLoop()
    try:
        mainloop.run()
    except KeyboardInterrupt:
        print("\n🛑 Đang tắt BLE Server...")
        ad_manager.UnregisterAdvertisement(adv.get_path())
        print("👋 Đã tắt.")