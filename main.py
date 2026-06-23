import os
import requests
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivy.clock import Clock
from kivy.utils import platform

# Plyer GPS aman di-import meskipun belum granted; error muncul saat .start()
from plyer import gps


class PhotoDetectorApp(MDApp):

    GPS_TIMEOUT_SECONDS = 30

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        self.layout = MDBoxLayout(orientation='vertical', padding=20, spacing=20)

        self.camera_widget = None  # dibuat belakangan, setelah permission granted

        self.capture_btn = MDRaisedButton(
            text="AMBIL FOTO & ACCES GPS HARDWARE",
            pos_hint={"center_x": 0.5},
            on_release=self.start_gps_and_capture
        )
        self.layout.add_widget(self.capture_btn)

        self.result_label = MDLabel(
            text="Metadata & Koordinat GPS akan muncul di sini...",
            halign="center",
            theme_text_color="Secondary"
        )
        self.layout.add_widget(self.result_label)

        self.current_lat = None
        self.current_lon = None
        self._gps_timeout_event = None

        return self.layout

    def on_start(self):
        # WAJIB: minta runtime permission SEBELUM kamera/gps dipakai.
        if platform == 'android':
            from android.permissions import request_permissions, Permission, check_permission

            needed = [
                Permission.CAMERA,
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION,
            ]

            missing = [p for p in needed if not check_permission(p)]
            if missing:
                request_permissions(missing, self.on_permissions_result)
            else:
                self.init_camera()
        else:
            self.init_camera()

    def on_permissions_result(self, permissions, grants):
        if all(grants):
            self.init_camera()
        else:
            self.result_label.text = (
                "Izin Kamera/GPS ditolak.\n"
                "Buka Settings > Apps > Phodec > Permissions untuk mengaktifkan."
            )

    def init_camera(self):
        from kivy.uix.camera import Camera

        if self.camera_widget is None:
            self.camera_widget = Camera(play=True, resolution=(640, 480))
            self.layout.add_widget(self.camera_widget, index=len(self.layout.children))
            self.result_label.text = "Kamera siap. Tekan tombol untuk ambil foto."

    def start_gps_and_capture(self, instance):
        if self.camera_widget is None:
            self.result_label.text = "Kamera belum siap."
            return

        self.result_label.text = "Mencari sinyal GPS (Menunggu lock...)"
        self.current_lat = None
        self.current_lon = None

        # Batalkan timeout event lama kalau ada sisa dari capture sebelumnya,
        # supaya gak numpuk timer dan gak ke-trigger di waktu yang salah.
        self._cancel_gps_timeout()

        try:
            gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
            gps.start()

            # INI YANG SEBELUMNYA HILANG: timeout 30s harus benar-benar dijadwalkan
            # di sini, kalau tidak, app akan menunggu on_gps_location selamanya
            # kalau GPS tidak pernah memberi fix.
            self._gps_timeout_event = Clock.schedule_once(
                self.gps_timeout, self.GPS_TIMEOUT_SECONDS
            )
        except Exception as e:
            self.result_label.text = f"GPS gagal: {str(e)}\nMengambil foto tanpa GPS..."
            Clock.schedule_once(self.trigger_capture, 1.0)

    def on_gps_location(self, **kwargs):
        # Kalau timeout sudah lebih dulu jalan (race condition), abaikan callback
        # supaya trigger_capture tidak terpanggil dua kali.
        if self._gps_timeout_event is None:
            return

        self.current_lat = kwargs.get('lat')
        self.current_lon = kwargs.get('lon')

        self._cancel_gps_timeout()

        try:
            gps.stop()
        except Exception:
            pass

        self.result_label.text = (
            f"GPS Terkunci: {self.current_lat}, {self.current_lon}\nMengambil foto..."
        )
        Clock.schedule_once(self.trigger_capture, 0.5)

    def on_gps_status(self, stype, status):
        # Berguna untuk debugging: status provider GPS (misalnya "provider-disabled").
        # Tampilkan sementara di label biar kelihatan progress-nya, tanpa
        # mengganggu countdown timeout.
        print(f"[GPS STATUS] {stype}: {status}")

    def gps_timeout(self, dt):
        self._gps_timeout_event = None
        if self.current_lat is None:
            try:
                gps.stop()
            except Exception:
                pass
            self.result_label.text = "GPS Timeout. Mengambil foto tanpa lokasi..."
            self.trigger_capture(0)

    def _cancel_gps_timeout(self):
        if self._gps_timeout_event is not None:
            self._gps_timeout_event.cancel()
            self._gps_timeout_event = None

    def trigger_capture(self, dt):
        try:
            self.filename = os.path.join(self.user_data_dir, "temp_capture.png")
            self.camera_widget.export_to_png(self.filename)
            self.result_label.text = "Mengirim gambar & data ke API..."
            Clock.schedule_once(lambda dt: self.send_to_server(self.filename), 0.3)
        except Exception as e:
            self.result_label.text = f"Gagal ambil foto: {str(e)}"

    def send_to_server(self, filepath):
        if not os.path.exists(filepath):
            self.result_label.text = "Gagal mengambil gambar."
            return

        try:
            # GANTI IP INI DENGAN IP LAPTOP LU
            TARGET_URL = "http://10.45.56.214:5000/api/upload"

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