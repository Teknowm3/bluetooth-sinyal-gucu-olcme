import asyncio
import threading
from bleak import BleakScanner, BleakClient
import tkinter as tk
from tkinter import messagebox

class BluetoothApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Bluetooth Bağlantı Durumu Uygulaması")

        self.label = tk.Label(master, text="Bluetooth Cihazlarını Taranıyor...")
        self.label.pack()

        self.listbox = tk.Listbox(master)
        self.listbox.pack()

        self.refresh_button = tk.Button(master, text="Yenile", command=self.refresh_devices)
        self.refresh_button.pack()

        self.connect_button = tk.Button(master, text="Bağlan", command=self.connect_device)
        self.connect_button.pack()

        self.status_label = tk.Label(master, text="Bağlantı Durumu: Bekleniyor...")
        self.status_label.pack()

        self.devices = []
        self.device_names = {}  # Cihaz isimlerini saklamak için bir sözlük
        self.client = None

        # İlk tarama işlemi için ayrı bir thread oluşturuluyor
        threading.Thread(target=self.run_async_task, args=(self.refresh_devices_async,)).start()

    def run_async_task(self, async_func):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_func())

    def refresh_devices(self):
        threading.Thread(target=self.run_async_task, args=(self.refresh_devices_async,)).start()

    async def refresh_devices_async(self):
        self.listbox.delete(0, tk.END)
        devices = await BleakScanner.discover()
        for device in devices:
            try:
                device_name = await self.get_device_name(device.address)
            except Exception:
                device_name = "Bilinmeyen Cihaz"
            self.device_names[device.address] = device_name
            self.listbox.insert(tk.END, f"{device_name} ({device.address}) - RSSI: {device.rssi}")
        self.label.config(text="Bluetooth Cihazları Tarandı")

    def connect_device(self):
        threading.Thread(target=self.run_async_task, args=(self.connect_device_async,)).start()

    async def connect_device_async(self):
        selected = self.listbox.curselection()
        if selected:
            device_info = self.listbox.get(selected[0])
            addr = device_info.split('(')[-1].split(')')[0]
            self.label.config(text=f"{addr} adresli cihaza bağlanılıyor...")
            try:
                self.client = BleakClient(addr)
                await self.client.connect()
                if self.client.is_connected:
                    device_name = self.device_names.get(addr, "Bilinmeyen Cihaz")
                    self.label.config(text=f"{device_name} ({addr}) adresli cihaza bağlandı")
                    # Bağlantıyı izlemek için ayrı bir thread oluşturuluyor
                    threading.Thread(target=self.monitor_connection).start()
            except Exception as err:
                self.label.config(text=f"Bağlantı hatası: {err}")
                messagebox.showerror("Bağlantı Hatası", f"Cihaza bağlanılamadı: {err}")

    def monitor_connection(self):
        asyncio.run(self.monitor_connection_async())

    async def monitor_connection_async(self):
        try:
            while self.client.is_connected:
                # Bağlantı sağlığını izleme işlemleri
                rssi = await self.get_signal_strength()
                signal_strength = self.calculate_signal_percentage(rssi)
                device_name = self.device_names.get(self.client.address, "Bilinmeyen Cihaz")
                self.status_label.config(text=f"{device_name} Bağlantı Sağlığı: {signal_strength}%")
                self.master.update_idletasks()
                await asyncio.sleep(0.3)  # Yenileme süresini 0.3 saniye olarak ayarla
        except Exception as err:
            self.label.config(text=f"Bağlantı kaybedildi: {err}")
            messagebox.showerror("Bağlantı Kaybı", "Cihaz ile bağlantı kesildi.")
            await self.disconnect_device()

    async def disconnect_device(self):
        if self.client:
            try:
                await self.client.disconnect()
            except Exception as err:
                self.label.config(text=f"Bağlantı kesilme hatası: {err}")
            finally:
                self.client = None
                self.status_label.config(text="Bağlantı Durumu: Bekleniyor...")

    async def get_signal_strength(self):
        # BleakClient'ta get_rssi metodu yoksa alternatif bir yol bulunmalıdır.
        # Bu örnek, direk rssi bilgisini scanner'dan alıyor.
        for _ in range(3):  # Birkaç kez dene
            devices = await BleakScanner.discover()
            device = next((d for d in devices if d.address == self.client.address), None)
            if device:
                return device.rssi
            await asyncio.sleep(1)  # Biraz bekle ve tekrar dene
        return -100  # Hiçbir sonuç bulunamazsa varsayılan değeri dön

    def calculate_signal_percentage(self, rssi):
        # RSSI değerini yüzdeye çeviren basit bir formül
        min_rssi = -100
        max_rssi = -50
        percentage = 100 * (rssi - min_rssi) / (max_rssi - min_rssi)
        return max(0, min(100, int(percentage)))

    async def get_device_name(self, address):
        async with BleakScanner() as scanner:
            devices = await scanner.discover()
            device = next((d for d in devices if d.address == address), None)
            if device:
                return device.name
            else:
                raise Exception("Cihaz adı alınamadı.")

if __name__ == "__main__":
    root = tk.Tk()
    app = BluetoothApp(root)
    root.mainloop()