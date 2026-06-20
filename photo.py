import os
import requests
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivy.uix.camera import Camera
from kivy.clock import Clock

# Library untuk mengakses hardware GPS di perangkat mobile
from plyer import gps

class PhotoDetectorApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=20)

        # 1. Kamera Widget (Live Preview)
        self.camera_widget = Camera(play=True, resolution=(640, 480))
        layout.add_widget(self.camera_widget)

        # 2. Tombol Ambil Foto
        self.capture_btn = MDRaisedButton(
            text="AMBIL FOTO & ACCES GPS HARDWARE",
            pos_hint={"center_x": 0.5},
            on_release=self.start_gps_and_capture
        )
        layout.add_widget(self.capture_btn)

        # 3. Output Label (Tempat memunculkan metadata)
        self.result_label = MDLabel(
            text="Metadata & Koordinat GPS akan muncul di sini...",
            halign="center",
            theme_text_color="Secondary"
        )
        layout.add_widget(self.result_label)

        # Variabel internal untuk menampung koordinat hardware sementara
        self.current_lat = None
        self.current_lon = None

        return layout

    def start_gps_and_capture(self, instance):
        self.result_label.text = "Mencari sinyal GPS dan mengunci lokasi..."
        try:
            # Mengaktifkan sensor GPS hardware via Plyer
            gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
            gps.start()
            
            # Berikan waktu 2 detik bagi hardware HP untuk mengunci titik koordinat sebelum menjepret
            Clock.schedule_once(self.trigger_capture, 2.0)
        except NotImplementedError:
            # Jika dijalankan di laptop (Windows/Mac) yang tidak punya sensor GPS native,
            # sistem otomatis melewati pencarian GPS agar tidak crash.
            self.result_label.text = "Hardware GPS tidak terdeteksi (Menjalankan mode kamera standar)..."
            Clock.schedule_once(self.trigger_capture, 1.0)

    def on_gps_location(self, **kwargs):
        # Fungsi ini otomatis berjalan saat sensor GPS HP berhasil mendapat koordinat
        self.current_lat = kwargs.get('lat')
        self.current_lon = kwargs.get('lon')
        gps.stop() # Matikan sensor kembali agar baterai tidak boros

    def on_gps_status(self, stype, status):
        pass

    def trigger_capture(self, dt):
        self.filename = "temp_capture.jpg"
        self.camera_widget.export_to_png(self.filename)
        self.result_label.text = "Mengirim gambar & data ke ExifTools API..."
        Clock.schedule_once(lambda dt: self.send_to_exiftools(self.filename), 0.1)

    def send_to_exiftools(self, filepath):
        if not os.path.exists(filepath):
            self.result_label.text = "Gagal mengambil gambar dari kamera."
            return

        try:
            # Endpoint resmi sesuai dokumentasi ExifTools
            TARGET_URL = "https://exiftools.com/api/v1/extract"
            
            # PENTING: Ganti string di bawah ini dengan API Key aslimu dari dashboard web
            MY_API_KEY = "87aeb8a6ca77bc4f" 
            
            headers = {
                "X-API-KEY": MY_API_KEY,
                "Authorization": f"Bearer {MY_API_KEY}"
            }
            
            # Memasukkan data koordinat hardware ke dalam parameter kiriman (payload)
            payload = {
                "hardware_latitude": self.current_lat,
                "hardware_longitude": self.current_lon
            }
            
            with open(filepath, 'rb') as f:
                # Mengirimkan file gambar murni via form-data sesuai dokumentasi
                files = {
                    'file': ('image.jpg', f, 'image/jpeg')
                }
                response = requests.post(TARGET_URL, headers=headers, files=files, data=payload, timeout=20)
            
            if response.status_code == 200:
                try:
                    res_json = response.json()
                    formatted_text = "=== METADATA BERHASIL DIEKSTRAK ===\n\n"
                    
                    # 1. Tampilkan Info Koordinat Hardware jika berhasil ditangkap Plyer (di HP)
                    if self.current_lat and self.current_lon:
                        formatted_text += f"[Hardware GPS] Lat: {self.current_lat} | Lon: {self.current_lon}\n"
                    
                    # 2. Tampilkan Info Struktur Utama Berkas dari Server
                    formatted_text += f"Status Server: {res_json.get('status', 'N/A')}\n"
                    formatted_text += f"Nama Berkas: {res_json.get('fileName', 'N/A')}\n\n"
                    
                    # 3. Membongkar sub-dictionary (EXIF, IPTC, dll) sesuai dokumentasi resmi
                    inner_metadata = res_json.get('metadata', {})
                    if isinstance(inner_metadata, dict):
                        count = 0
                        for category, tags in inner_metadata.items():
                            if isinstance(tags, dict):
                                for tag_name, tag_value in tags.items():
                                    if count < 15: # Batasi 15 baris teks agar muat di layar HP
                                        formatted_text += f"[{category}] {tag_name}: {tag_value}\n"
                                        count += 1
                            else:
                                if count < 15:
                                    formatted_text += f"{category}: {tags}\n"
                                    count += 1
                                    
                    self.result_label.text = formatted_text
                except Exception:
                    self.result_label.text = f"=== RESPONS ===\n\n{response.text[:400]}"
            else:
                self.result_label.text = f"ExifTools Menolak! (Code {response.status_code})\nRespon: {response.text[:150]}"
        
        except requests.exceptions.RequestException as e:
            self.result_label.text = f"Koneksi Gagal!\nError: {str(e)}"
        
        finally:
            # Reset koordinat dan hapus file sementara setelah selesai
            self.current_lat = None
            self.current_lon = None
            if os.path.exists(filepath):
                os.remove(filepath)

if __name__ == '__main__':
    PhotoDetectorApp().run()