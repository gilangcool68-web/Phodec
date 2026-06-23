from flask import Flask, request, render_template_string, jsonify, redirect, url_for, send_from_directory
import sqlite3
import datetime
import os
import time
from PIL import Image, ExifTags

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. EXIF PARSER
def get_exif_data(filepath):
    exif_html = "<tr><td colspan='2' class='text-center text-danger'>NO METADATA DETECTED</td></tr>"
    lat_deg = "Tidak ada"
    lon_deg = "Tidak ada"
    
    try:
        img = Image.open(filepath)
        exif_data = img._getexif()
        
        info = []
        gps_info = {}
        
        file_size = os.path.getsize(filepath)
        info.append(f"<tr><td class='key-col'>File Size</td><td class='val-col'>{file_size / 1024:.2f} KB</td></tr>")
        info.append(f"<tr><td class='key-col'>Image Format</td><td class='val-col'>{img.format}</td></tr>")
        info.append(f"<tr><td class='key-col'>Image Size</td><td class='val-col'>{img.width} x {img.height} px</td></tr>")
        info.append(f"<tr><td class='key-col'>Color Mode</td><td class='val-col'>{img.mode}</td></tr>")
        
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes): continue
                    
                if tag == 'GPSInfo':
                    gps_info = value
                else:
                    info.append(f"<tr><td class='key-col'>{tag}</td><td class='val-col'>{value}</td></tr>")
                    
        if info:
            exif_html = "".join(info)
            
        if gps_info:
            try:
                def convert_to_degrees(value):
                    d = float(value[0])
                    m = float(value[1])
                    s = float(value[2])
                    return d + (m / 60.0) + (s / 3600.0)

                lat = convert_to_degrees(gps_info[2])
                if gps_info[1] == 'S': lat = -lat
                
                lon = convert_to_degrees(gps_info[4])
                if gps_info[3] == 'W': lon = -lon
                
                lat_deg = f"{lat:.6f}"
                lon_deg = f"{lon:.6f}"
            except Exception:
                pass 
                
    except Exception as e:
        exif_html = f"<tr><td colspan='2' class='text-danger'>Error: {str(e)}</td></tr>"
        
    return exif_html, lat_deg, lon_deg

# 2. INISIASI DATABASE
def init_db():
    conn = sqlite3.connect('metadata.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS photo_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT, waktu_masuk TEXT, lat TEXT, lon TEXT,
        nama_file TEXT, exif_data TEXT, status TEXT)''')
    conn.commit()
    conn.close()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# 3. ENDPOINT API TERIMA FOTO (Dari HP Android)
@app.route('/api/upload', methods=['POST'])
def receive_data():
    hw_lat = request.form.get('hardware_latitude', 'Tidak ada')
    hw_lon = request.form.get('hardware_longitude', 'Tidak ada')
    
    file = request.files.get('file')
    nama_file = "Tidak_ada_gambar.jpg"
    exif_html = ""
    final_lat, final_lon = hw_lat, hw_lon
    
    if file and file.filename != '':
        nama_file = f"{int(time.time())}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, nama_file)
        file.save(filepath)
        
        exif_html, exif_lat, exif_lon = get_exif_data(filepath)
        final_lat = exif_lat if exif_lat != "Tidak ada" else hw_lat
        final_lon = exif_lon if exif_lon != "Tidak ada" else hw_lon

    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('metadata.db')
    c = conn.cursor()
    c.execute("INSERT INTO photo_data (waktu_masuk, lat, lon, nama_file, exif_data, status) VALUES (?, ?, ?, ?, ?, ?)",
              (waktu, final_lat, final_lon, nama_file, exif_html, "Android Node"))
    conn.commit()
    conn.close()

    return jsonify({"status": "sukses", "fileName": nama_file}), 200

# 4. ENDPOINT DASHBOARD UTAMA
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        file = request.files.get('file_web')
        if file and file.filename != '':
            nama_file = f"{int(time.time())}_web_{file.filename}"
            filepath = os.path.join(UPLOAD_FOLDER, nama_file)
            file.save(filepath)
            
            waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            exif_html, exif_lat, exif_lon = get_exif_data(filepath)
            
            conn = sqlite3.connect('metadata.db')
            c = conn.cursor()
            c.execute("INSERT INTO photo_data (waktu_masuk, lat, lon, nama_file, exif_data, status) VALUES (?, ?, ?, ?, ?, ?)",
                      (waktu, exif_lat, exif_lon, nama_file, exif_html, "Web Inject"))
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))

    conn = sqlite3.connect('metadata.db')
    c = conn.cursor()
    c.execute("SELECT * FROM photo_data ORDER BY id DESC")
    data = c.fetchall()
    total_data = len(data)
    conn.close()

    html_template = """
    <!DOCTYPE html>
    <html lang="id" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PHODEC - Command Center</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@^4.0.0/dist/maplibre-gl.css" />
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
            body { background-color: #050b14; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; background-image: radial-gradient(#1e293b 1px, transparent 1px); background-size: 20px 20px; }
            .navbar { background-color: rgba(15, 23, 42, 0.95) !important; border-bottom: 1px solid #00f0ff; backdrop-filter: blur(10px); }
            .brand-text { font-family: 'Share Tech Mono', monospace; letter-spacing: 2px; color: #00f0ff; }
            .card { background-color: rgba(15, 23, 42, 0.85); border: 1px solid #1e293b; border-radius: 6px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5); }
            .card-header { background-color: #0b0f19; border-bottom: 1px solid #1d4ed8; font-family: 'Share Tech Mono', monospace; color: #00f0ff; }
            .btn-cyber { background-color: transparent; border: 1px solid #00f0ff; color: #00f0ff; transition: 0.3s; font-family: 'Share Tech Mono'; }
            .btn-cyber:hover { background-color: #00f0ff; color: #050b14; box-shadow: 0 0 10px #00f0ff; }
            .table-dark th { background-color: #0b0f19; color: #94a3b8; font-family: 'Share Tech Mono', monospace; font-size: 0.85rem; }
            .table-dark td { background-color: rgba(15, 23, 42, 0.6); vertical-align: middle; border-color: #1e293b; }
            .exif-container { max-height: 150px; overflow-y: auto; background: #000; border: 1px solid #334155; border-radius: 4px; }
            .exif-table { width: 100%; font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; margin: 0; }
            .exif-table td { padding: 4px 8px; border-bottom: 1px solid #1e293b; }
            .key-col { color: #94a3b8; width: 40%; font-weight: bold; }
            .val-col { color: #4ade80; }
            .cursor-pointer { cursor: pointer; transition: 0.2s; font-family: 'Share Tech Mono', monospace; }
            .cursor-pointer:hover { color: #00f0ff !important; text-shadow: 0 0 5px rgba(0, 240, 255, 0.5); }
            .map-container { height: 300px; width: 100%; display: none; margin-top: 10px; border: 1px solid #00f0ff; border-radius: 4px; }
            .modal-content { background: #050b14; border: 1px solid #00f0ff; box-shadow: 0 0 20px rgba(0, 240, 255, 0.2); }
            .modal-header { border-bottom: 1px solid #1d4ed8; }
            .modal-footer { border-top: 1px solid #1d4ed8; }
            .modal-image-container img { object-fit: contain; max-height: 80vh; width: 100%; border-radius: 4px; }
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark mb-4 py-2">
            <div class="container-fluid px-4">
                <a class="navbar-brand d-flex align-items-center" href="/">
                    <img src="/uploads/icon.png" width="30" height="30" class="me-3" style="border-radius: 4px;" onerror="this.style.display='none'">
                    <span class="brand-text fw-bold fs-5">PHODEC</span> <span class="ms-2 text-secondary" style="font-size: 0.9rem;">| SECURE TERMINAL</span>
                </a>
            </div>
        </nav>

        <div class="container-fluid px-4">
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="card-body text-center d-flex flex-column justify-content-center">
                            <h6 class="text-secondary fw-bold font-monospace">TOTAL TARGETS</h6>
                            <h2 class="fw-bold mb-0" style="color: #00f0ff; text-shadow: 0 0 10px rgba(0,240,255,0.3);">{{ total_data }}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-9">
                    <div class="card h-100">
                        <div class="card-header"><i class="fas fa-terminal me-2"></i> INJECT DATA MANUAL</div>
                        <div class="card-body">
                            <form method="POST" enctype="multipart/form-data" class="d-flex gap-3">
                                <input class="form-control bg-dark text-info border-secondary" type="file" name="file_web" accept="image/*" required>
                                <button type="submit" class="btn btn-cyber px-4"><i class="fas fa-upload"></i> EXECUTE</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card mb-5">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-network-wired me-2"></i> LIVE INTEL LOGS</span>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-dark table-hover mb-0">
                            <thead>
                                <tr>
                                    <th class="ps-4">UID</th>
                                    <th>TIMESTAMP</th>
                                    <th>GEOLOCATION</th>
                                    <th>METADATA DUMP</th>
                                    <th>NODE</th>
                                    <th class="text-center pe-4">ACTION</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in data %}
                                <tr>
                                    <td class="ps-4 fw-bold" style="color: #00f0ff;">#{{ row[0] }}</td>
                                    <td class="text-secondary" style="font-family: 'Share Tech Mono'; font-size:0.85rem;">{{ row[1] }}</td>
                                    <td>
                                        <div class="cursor-pointer text-danger fw-bold" onclick="toggleMap('map-{{ row[0] }}', '{{ row[2] }}', '{{ row[3] }}')">
                                            <i class="fas fa-crosshairs me-1"></i> LAT: {{ row[2] }}<br><i class="fas fa-crosshairs me-1"></i> LON: {{ row[3] }}
                                        </div>
                                        <div id="map-{{ row[0] }}" class="map-container"></div>
                                    </td>
                                    <td style="width: 35%;">
                                        <div class="exif-container">
                                            <table class="exif-table">{{ row[5]|safe }}</table>
                                        </div>
                                    </td>
                                    <td><span class="badge border border-info text-info bg-transparent">{{ row[6] }}</span></td>
                                    <td class="text-center pe-4">
                                        <a href="/report/{{ row[0] }}" target="_blank" class="btn btn-sm btn-outline-warning mb-1 w-100 font-monospace" style="font-size:0.75rem;">
                                            <i class="fas fa-external-link-alt"></i> REPORT
                                        </a>
                                        <button class="btn btn-sm btn-cyber w-100 font-monospace" data-bs-toggle="modal" data-bs-target="#modal-img-{{ row[0] }}" style="font-size:0.75rem;">
                                            <i class="fas fa-eye"></i> VIEW
                                        </button>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        {% for row in data %}
        <div class="modal fade" id="modal-img-{{ row[0] }}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h6 class="modal-title" style="color: #00f0ff; font-family: 'Share Tech Mono';"><i class="fas fa-file-image me-2"></i> ASSET: {{ row[4] }}</h6>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-2 modal-image-container text-center bg-black">
                        <img src="/uploads/{{ row[4] }}" alt="Target Asset">
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-outline-info btn-sm font-monospace" data-bs-dismiss="modal">CLOSE</button>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}

        <script src="https://unpkg.com/maplibre-gl@^4.0.0/dist/maplibre-gl.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            var activeMaps = {}; 
            function toggleMap(mapId, lat, lon) {
                var mapDiv = document.getElementById(mapId);
                if (mapDiv.style.display === "none") {
                    var latNum = parseFloat(lat); var lonNum = parseFloat(lon);
                    if (isNaN(latNum) || isNaN(lonNum)) { mapDiv.style.display = "block"; mapDiv.innerHTML = "<div class='text-center text-danger fw-bold mt-4'>NO GPS SIGNAL</div>"; return; }
                    mapDiv.style.display = "block"; mapDiv.innerHTML = ""; 
                    var map = new maplibregl.Map({
                        container: mapId, preserveDrawingBuffer: true,
                        style: { "version": 8, "sources": { "carto": { "type": "raster", "tiles": ["https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png"], "tileSize": 256 } }, "layers": [{ "id": "carto", "type": "raster", "source": "carto" }] },
                        center: [lonNum, latNum], zoom: 15
                    });
                    map.addControl(new maplibregl.NavigationControl(), 'top-right');
                    map.addControl(new maplibregl.FullscreenControl(), 'top-left');
                    new maplibregl.Marker({ color: '#dc3545' }).setLngLat([lonNum, latNum]).addTo(map);
                    activeMaps[mapId] = map;
                    setTimeout(function() { map.resize(); }, 200);
                } else {
                    mapDiv.style.display = "none";
                    if (activeMaps[mapId]) { activeMaps[mapId].remove(); delete activeMaps[mapId]; }
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, data=data, total_data=total_data)

# 5. ENDPOINT DOSSIER SHARE REPORT (TACTICAL UI)
@app.route('/report/<int:id>')
def target_report(id):
    conn = sqlite3.connect('metadata.db')
    c = conn.cursor()
    c.execute("SELECT * FROM photo_data WHERE id=?", (id,))
    row = c.fetchone()
    conn.close()
    
    if not row: return "<h2 style='color:red; text-align:center; margin-top:50px;'>DATA NOT FOUND</h2>", 404

    report_template = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PHODEC DOSSIER #{{ row[0] }}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@^4.0.0/dist/maplibre-gl.css" />
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
            body { background-color: #0a0f1a; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
            .dossier-container { max-width: 900px; margin: 20px auto; background: #050b14; border: 1px solid #1d4ed8; box-shadow: 0 0 30px rgba(0, 240, 255, 0.1); position: relative; }
            .dossier-header { background: #0b0f19; border-bottom: 2px solid #00f0ff; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; }
            .dossier-title { font-family: 'Share Tech Mono', monospace; color: #00f0ff; font-size: 1.5rem; margin: 0; }
            .target-id { color: #dc3545; font-weight: bold; font-family: 'Share Tech Mono'; font-size: 1.2rem; }
            .dossier-body { padding: 30px; }
            .section-title { color: #00f0ff; font-family: 'Share Tech Mono', monospace; font-size: 1.1rem; border-bottom: 1px solid #1e293b; padding-bottom: 5px; margin-bottom: 15px; text-transform: uppercase; }
            .asset-img { width: 100%; border: 1px solid #334155; border-radius: 4px; background: #000; padding: 5px; }
            .meta-table { width: 100%; font-family: 'Share Tech Mono', monospace; font-size: 0.8rem; }
            .meta-table td { padding: 8px 10px; border: 1px solid #1e293b; }
            .meta-table .key-col { background: #0b0f19; color: #94a3b8; font-weight: bold; width: 35%; }
            .meta-table .val-col { background: #050b14; color: #4ade80; word-break: break-all; }
            .map-box { height: 280px; width: 100%; border: 1px solid #1d4ed8; border-radius: 4px; }
            .dossier-footer { background: #0b0f19; padding: 10px 30px; border-top: 1px solid #1e293b; font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; color: #64748b; text-align: center; }
            @media print {
                body, .dossier-container { background-color: #050b14 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                .dossier-header { background-color: #0b0f19 !important; border-bottom: 2px solid #00f0ff !important; }
                .meta-table .key-col { background-color: #0b0f19 !important; color: #94a3b8 !important; }
                .meta-table .val-col { background-color: #050b14 !important; color: #4ade80 !important; }
                .no-print { display: none !important; }
                .dossier-container { margin: 0; border: none; box-shadow: none; }
            }
        </style>
    </head>
    <body>
        <div class="text-center mt-3 mb-2 no-print">
            <button onclick="window.close()" class="btn btn-outline-secondary btn-sm font-monospace me-2"><i class="fas fa-times"></i> CLOSE TERMINAL</button>
            <button onclick="downloadPDF()" class="btn btn-outline-info btn-sm font-monospace"><i class="fas fa-download me-2"></i> EXPORT TO SECURE PDF</button>
        </div>

        <div class="dossier-container" id="printable-area">
            <div class="dossier-header">
                <div>
                    <h1 class="dossier-title"><i class="fas fa-fingerprint me-2"></i>PHODEC INTELLIGENCE DOSSIER</h1>
                    <div style="font-family: 'Share Tech Mono'; font-size: 0.8rem; color: #64748b; margin-top: 5px;">EXTRACTED: {{ row[1] }}</div>
                </div>
                <div class="text-end">
                    <div class="target-id">TARGET UID #{{ row[0] }}</div>
                    <div style="font-size: 0.7rem; color: #dc3545; font-weight: bold; letter-spacing: 1px;"><i class="fas fa-lock me-1"></i> CLASSIFIED</div>
                </div>
            </div>

            <div class="dossier-body row">
                <div class="col-md-5">
                    <div class="section-title"><i class="fas fa-camera me-2"></i> VISUAL EVIDENCE</div>
                    <img src="/uploads/{{ row[4] }}" class="asset-img mb-4" alt="Target Image">
                    
                    <div class="section-title"><i class="fas fa-satellite-dish me-2"></i> GEOLOCATION</div>
                    <div class="mb-2 text-center" style="font-family: 'Share Tech Mono'; color: #00f0ff; border: 1px dashed #1d4ed8; padding: 5px; background: #0b0f19;">
                        LAT: {{ row[2] }} &nbsp;|&nbsp; LON: {{ row[3] }}
                    </div>
                    <div id="static-map" class="map-box"></div>
                </div>

                <div class="col-md-7">
                    <div class="section-title"><i class="fas fa-microchip me-2"></i> METADATA / EXIF DUMP</div>
                    <table class="meta-table">
                        <tbody>
                            {{ row[5]|safe }}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="dossier-footer">
                SYSTEM GENERATED REPORT | PHODEC TACTICAL NODE | UNAUTHORIZED DISTRIBUTION PROHIBITED
            </div>
        </div>

        <script src="https://unpkg.com/maplibre-gl@^4.0.0/dist/maplibre-gl.js"></script>
        <script>
            var latNum = parseFloat("{{ row[2] }}");
            var lonNum = parseFloat("{{ row[3] }}");
            var mapDiv = document.getElementById('static-map');
            
            if (!isNaN(latNum) && !isNaN(lonNum)) {
                var map = new maplibregl.Map({
                    container: 'static-map',
                    preserveDrawingBuffer: true,
                    style: {
                        "version": 8,
                        "sources": { "carto": { "type": "raster", "tiles": ["https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png"], "tileSize": 256 } },
                        "layers": [{ "id": "carto", "type": "raster", "source": "carto" }]
                    },
                    center: [lonNum, latNum], zoom: 15, interactive: false
                });
                new maplibregl.Marker({ color: '#dc3545' }).setLngLat([lonNum, latNum]).addTo(map);
            } else {
                mapDiv.innerHTML = "<div class='d-flex justify-content-center align-items-center h-100 text-danger fw-bold font-monospace' style='background: #0b0f19;'>NO GPS SIGNAL TRACED</div>";
            }

            function downloadPDF() {
                var element = document.getElementById('printable-area');
                var opt = {
                    margin:       0,
                    filename:     'PHODEC_DOSSIER_UID{{ row[0] }}.pdf',
                    image:        { type: 'jpeg', quality: 1.0 },
                    html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#050b14' },
                    jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
                };
                html2pdf().set(opt).from(element).save();
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(report_template, row=row)

if __name__ == '__main__':
    init_db()
    print("=====================================================")
    print(" [+] PHODEC TACTICAL SERVER SECURED ")
    print(" [+] ACCESS TERMINAL: http://127.0.0.1:5000")
    print("=====================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)