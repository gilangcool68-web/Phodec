import os
import requests
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivy.uix.camera import Camera
from kivy.clock import Clock
from plyer import gps

class PhotoDetectorApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=20)

        # 1. Kamera Widget
        self.camera_widget = Camera(play=True, resolution=(640, 480))
        layout.add_widget(self.camera_widget)

        # 2. Tombol
        self.capture_btn = MDRaisedButton(
            text="AMBIL FOTO & ACCES GPS HARDWARE",
            pos_hint={"center_x": 0.5},
            on_release=self.start_gps_and_capture
        )
        layout.add_widget(self.capture_btn)

        # 3. Label Output
        self.result_label = MDLabel(
            text="Metadata & Koordinat GPS akan muncul di sini...",
            halign="center",
            theme_text_color="Secondary"
        )
        layout.add_widget(self.result_label)

        self.current_lat = None
        self.current_lon = None

        return layout

    def start_gps_and_capture(self, instance):
        self.result_label.text = "Mencari sinyal GPS dan mengunci lokasi..."
        try:
            gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
            gps.start()
            Clock.schedule_once(self.trigger_capture, 2.0)
        except NotImplementedError:
            self.result_label.text = "Hardware GPS tidak terdeteksi (Menjalankan mode kamera standar)..."
            Clock.schedule_once(self.trigger_capture, 1.0)

    def on_gps_location(self, **kwargs):
        self.current_lat = kwargs.get('lat')
        self.current_lon = kwargs.get('lon')
        gps.stop()

    def on_gps_status(self, stype, status):
        pass

    def trigger_capture(self, dt):
        self.filename = "temp_capture.png"
        self.camera_widget.export_to_png(self.filename)
        self.result_label.text = "Mengirim gambar & data ke API..."
        Clock.schedule_once(lambda dt: self.send_to_server(self.filename), 0.1)

    def send_to_server(self, filepath):
        if not os.path.exists(filepath):
            self.result_label.text = "Gagal mengambil gambar."
            return

        try:
            # GANTI IP INI DENGAN IP LAPTOP LU
            TARGET_URL = "http://10.0.42.92:5000/api/upload"
            
            payload = {
                "hardware_latitude": self.current_lat,
                "hardware_longitude": self.current_lon
            }
            
            with open(filepath, 'rb') as f:
                files = {'file': ('image.png', f, 'image/png')}
                response = requests.post(TARGET_URL, files=files, data=payload, timeout=20)
            
            if response.status_code == 200:
                res_json = response.json()
                self.result_label.text = f"=== SUKSES ===\nStatus: {res_json.get('status')}\nFile: {res_json.get('fileName')}"
            else:
                self.result_label.text = f"Ditolak! Code: {response.status_code}"
        
        except requests.exceptions.RequestException as e:
            self.result_label.text = f"Koneksi Gagal!\nError: {str(e)}"
        
        finally:
            self.current_lat = None
            self.current_lon = None
            if os.path.exists(filepath):
                os.remove(filepath)

if __name__ == '__main__':
    PhotoDetectorApp().run()
