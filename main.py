import json
import os
import random
import socket
import sys
import threading
from contextlib import closing
from http.server import SimpleHTTPRequestHandler, HTTPServer

import folium
import requests
from PySide6.QtCore import Qt, QSize, QSettings, QUrl, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QScrollArea, QButtonGroup, QDialog, QFormLayout, QLineEdit, QSpinBox,
    QDialogButtonBox, QMessageBox, QGraphicsDropShadowEffect
)
from shapely import wkb

from GSITitleBar import QSITitleBar


class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()


class MWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if "webkitStorageInfo" in message:
            return  # Filter warning ini
        print(f"IKI LO: [JS-{level}] {message} (line {lineNumber})")

class LocationInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings("Kho Ming Suun", "Geo Spatial")
        self.default_lat = self.settings.value("last_lat", type=float)
        self.default_lon = self.settings.value("last_lon", type=float)
        self.default_key = self.settings.value("last_keyword")
        self.default_rad = self.settings.value("last_rad", type=int)

        self.setWindowTitle("Input Kunci Pencarian dan Lokasi")
        self.setup_ui()

        self.setStyleSheet("""
                    QDialog {
                        background-color: #2d2d2d;
                        color: #ffffff;
                        font-family: Arial;
                    }
                    QLabel {
                        color: #ffffff;
                        background-color: transparent;
                        padding: 4px;
                        border: none;
                    }
                    QFormLayout {
                        background-color: transparent;
                    }
                """)

    def get_inputs(self):
        return {
            'latitude': float(self.lat_input.text()),
            'longitude': float(self.lon_input.text()),
            'keyword': self.keyword.text(),
            'radius': self.radius_input.value()
        }

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Latitude Input
        self.lat_input = QLineEdit(str(self.default_lat))
        self.lat_input.setPlaceholderText(f"Contoh: {self.default_lat}")
        self.lat_input.setEnabled(False)
        self.lat_input.setMinimumWidth(300)
        self.lat_input.setStyleSheet("""
            QLineEdit:disabled {
                background-color: #3d3d3d;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        form_layout.addRow("Latitude:", self.lat_input)

        # Longitude Input
        self.lon_input = QLineEdit(str(self.default_lon))
        self.lon_input.setPlaceholderText(f"Contoh: {self.default_lon}")
        self.lon_input.setEnabled(False)
        self.lon_input.setStyleSheet("""
            QLineEdit:disabled {
                background-color: #3d3d3d;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        form_layout.addRow("Longitude:", self.lon_input)

        # Input keyword
        self.keyword = QLineEdit(str(self.default_key) if self.default_key else "")
        self.keyword.setPlaceholderText("Input keyword...")
        self.keyword.setToolTip("Input keyword untuk pencarian titik")
        self.keyword.setStyleSheet("""
            QLineEdit {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                selection-background-color: #0078d7;
            }
            QLineEdit:focus {
                border: 2px solid #0078d7;
            }
            QLineEdit::placeholder {
                color: #888888;
            }
        """)
        form_layout.addRow("Keyword:", self.keyword)

        # Radius Input
        self.radius_input = QSpinBox()
        self.radius_input.setRange(100, 5000000)
        self.radius_input.setValue(self.default_rad if self.default_rad else 6000)
        self.radius_input.setSingleStep(100)
        self.radius_input.setToolTip("Input nilai radius pencarian dalam meter")
        self.radius_input.setAccelerated(True)
        self.radius_input.setWrapping(True)
        self.radius_input.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                color: #ffffff;
                font-family: Arial;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
                padding: 4px;
                border: none;
            }
            QFormLayout {
                background-color: transparent;
            }
            QSpinBox {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                min-width: 100px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #4d4d4d;
                border: 1px solid #555555;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #5d5d5d;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 8px;
                height: 8px;
            }
            QSpinBox::up-arrow {
                image: url(none);
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 6px solid #ffffff;
            }
            QSpinBox::down-arrow {
                image: url(none);
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #ffffff;
            }
        """)
        form_layout.addRow("Radius (meter):", self.radius_input)

        layout.addLayout(form_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.setStyleSheet("""
            QPushButton {
                background-color: #4d4d4d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5d5d5d;
            }
            QPushButton:pressed {
                background-color: #3d3d3d;
            }
            QPushButton:focus {
                border: 2px solid #0078d7;
            }
        """)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

def wkbhex_to_latlon(wkb_hex: str):
    """
    Konversi WKB HEX POINT ke (latitude, longitude).
    """
    try:
        geom = wkb.loads(bytes.fromhex(wkb_hex))
        if geom.geom_type != "Point":
            raise ValueError("Geometry bukan POINT")

        xlon, xlat = geom.x, geom.y
        return xlat, xlon
    except Exception as e:
        print("Input Salah:", e)
        return None

class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings("Kho Ming Suun", "Geo Spatial")

        defaults = {
            "last_keyword": "SMA",
            "last_lat": -7.557924,
            "last_lon": 110.786439,
            "last_layer": 1,
            "last_rad": 6000,
            "last_token": "unauthorized",
            "last_image_profile": "https://www.python.org/static/community_logos/python-logo.png",
            "last_username": "Alice"
        }
        for key, value in defaults.items():
            if self.settings.value(key) is None:
                self.settings.setValue(key, value)

        self.first_titik_pusat = None
        self.server_port = 0
        self.browser = None
        self.submit_btn = None
        self.form_layout = None
        self.form_container = None
        self.main_layout = None
        self.token_input = ""

        self.m = None
        self.current_zoom = 14

        # Setup server
        self.server_port = self.find_free_port()
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()

        # UI Setup
        self.setup_ui()

        # Generate initial map
        QTimer.singleShot(100, self.generate_map)

    def find_free_port(self):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_port = s.getsockname()[1]
            return s.getsockname()[1]

    def run_server(self):
        server_address = ('', self.server_port)
        httpd = HTTPServer(server_address, CORSRequestHandler)
        print(f"Server berjalan di port {self.server_port}")
        httpd.serve_forever()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0,0,0,0)

        # Input Form
        self.form_container = QWidget()
        self.form_layout = QFormLayout(self.form_container)
        self.form_layout.setSpacing(0)
        self.form_layout.setContentsMargins(0,0,0,0)

        self.submit_btn = QPushButton("Klik disini untuk refresh map & mencari Lokasi")
        self.submit_btn.clicked.connect(self.open_dialog)
        self.submit_btn.setStyleSheet("""
            QPushButton{
                color: #ffffff;
                background-color: grey;
                padding: 4px;
                border: none;
                }"""
        )
        self.form_layout.addRow(self.submit_btn)
        self.main_layout.addWidget(self.form_container)

        # Web View
        self.browser = QWebEngineView()
        self.main_layout.addWidget(self.browser, stretch=1)


    def open_dialog(self):
        # token = self.token_input.strip()
        token = self.settings.value("last_token")
        if token:
            try:
                headers = {"Authorization": token}
                params = {}

                response = requests.get(
                    f"http://localhost:8000/locations/pusat/",
                    headers=headers,
                    params=params,
                    timeout=5
                )
                response.raise_for_status()
                locs = response.json()
                m_wkt_point = locs['coordinates']
                m_latitude, m_longitude = wkbhex_to_latlon(m_wkt_point)
                lat = round(float(m_latitude), 6)
                lon = round(float(m_longitude), 6)
                self.settings.setValue("last_lat", lat)
                self.settings.setValue("last_lon", lon)
            except:
                return
        else:
            pass

        dialog = LocationInputDialog(parent=self)

        if dialog.exec() == QDialog.Accepted:
            if inputs := dialog.get_inputs():
                self.settings.setValue("last_lat", float(inputs['latitude']))
                self.settings.setValue("last_lon", float(inputs['longitude']))
                self.settings.setValue("last_keyword", inputs['keyword'])
                self.settings.setValue("last_rad", int(inputs['radius']))
                self.generate_map()
            else:
                QMessageBox.warning(self, "Error", "Input tidak valid")
        else:
            pass

    def generate_map(self):
        try:
            # active_layer = self.settings.value("last_layer", type=int)
            lat = self.settings.value("last_lat", type=float)
            lon = self.settings.value("last_lon", type=float)
            keyword = self.settings.value("last_keyword")
            radius = self.settings.value("last_rad", type=int)
            token = self.settings.value("last_token")
            # token = self.token_input.strip()
            css_style = """
                <style>
                .custom-tooltip {
                    border-radius: 15px !important;
                    background: white !important;
                    padding: 10px !important;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
                    font-family: Arial !important;
                }
                .dashed-connection-line {
                    filter: drop-shadow(0px 0px 1px rgba(10,10,10,0.3));
                }

                .leaflet-control-container .leaflet-top.leaflet-right {
                    margin-top: 60px;
                }

                .route-control-button {
                    margin: 2px;
                    padding: 5px 10px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 12px;
                }

                .route-control-button:hover {
                    background: #0056b3;
                }

                .route-control-container {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    z-index: 1000;
                    background: white;
                    padding: 10px;
                    border-radius: 5px;
                    box-shadow: 0 0 5px rgba(0,0,0,0.3);
                    font-family: Arial, sans-serif;
                }
                </style>
                """
            marker_js_data = []
            current_zoom = self.m.get_zoom() if hasattr(self, 'm') and hasattr(self.m, 'get_zoom') else 14

            self.m = folium.Map(location=[lat, lon], zoom_start=current_zoom, tiles=None, max_zoom=16)

            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Esri Topo',
                max_zoom=16
            ).add_to(self.m)

            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri Satellite',
                name='Satellite View',
                overlay=False,
                control=True,
                max_zoom=18
            ).add_to(self.m)

            folium.TileLayer(
                tiles='openstreetmap',
                name='Open Street Maps',
                attr='OpenStreetMap contributors',
                max_zoom=19
            ).add_to(self.m)

            if token:
                try:
                    headers = {"Authorization": token}
                    params = {}

                    response = requests.get(
                        f"http://localhost:8000/locations/pusat/",
                        headers=headers,
                        params=params,
                        timeout=5
                    )
                    response.raise_for_status()
                    locs = response.json()
                    m_wkt_point = locs['coordinates']
                    m_latitude, m_longitude = wkbhex_to_latlon(m_wkt_point)
                    lat = m_latitude
                    lon = m_longitude

                    self.m.location = [lat, lon]

                    titik_pusat_content = f"""
                        <div style="font-size: 16px; font-family: Arial;">
                        <b>TITIK PUSAT</b><br><br>
                        Lat: {lat:.6f}<br>Lon: {lon:.6f}
                        <div style="font-size: 14px; font-family: Arial;">
                        <b>Jangkauan radius geodesic:</b> {float(radius)} meter<br>
                        </div></div>
                    """

                    # Titik pusat
                    self.first_titik_pusat = folium.Marker(
                        [lat, lon],
                        popup=folium.Popup(titik_pusat_content, max_width=500),
                        icon=folium.Icon(color="red", icon="star", prefix="fa")
                    ).add_to(self.m)

                    self.circle_layer = folium.FeatureGroup(name="Radius Jangkauan", show=False)

                    folium.Circle(
                        location=[lat, lon],
                        radius=float(radius),
                        color='red',
                        fill=True,
                        fill_color='red',
                        fill_opacity=0.2,
                        popup=f"Radius: {float(radius)} meter"
                    ).add_to(self.circle_layer)
                    self.circle_layer.add_to(self.m)

                except requests.exceptions.RequestException as e:
                    QMessageBox.warning(self, "API Error", f"Gagal mengambil data: {str(e)}")
            else:
                return

            with open("geo_json/33.72_kecamatan.geojson", "r", encoding="utf-8") as f:
                data = json.load(f)

            gl = folium.GeoJson(
                data,
                name="Batas Kecamatan",
                style_function=lambda feature: {
                    "fillColor": "red",
                    "color": "white",
                    "weight": 2,
                    "fillOpacity": 0.1,
                },
            ).add_to(self.m)

            if token:
                try:
                    headers = {"Authorization": token}
                    params = {
                        "longitude": lon,
                        "latitude": lat,
                        "keyword": keyword,
                        "radius": radius
                    }

                    response = requests.get(
                        f"http://localhost:8000/locations/nearby/search/?q={keyword}",
                        headers=headers,
                        params=params,
                        timeout=5
                    )
                    response.raise_for_status()
                    locs = response.json()
                    locations = locs["results"]

                    locations_feature_group = folium.FeatureGroup(
                        name="📍 Lokasi Terdekat",
                        show=True  # Tampilkan secara default
                    ).add_to(self.m)

                    for loc in locations:
                        try:
                            loc_lat = loc.get('latitude')
                            loc_lon = loc.get('longitude')
                            name = loc.get('name', 'Unknown')
                            distance = loc.get('exact_distance_meter', 'N/A')
                            duration = loc.get('exact_duration_minute')
                            address = loc.get('alamat', 'Alamat tidak tersedia')
                            fasilitas = ', '.join(loc.get('details', {}).get('fasilitas', []))
                            level = int(random.choice([1, 2, 3]))

                            if loc_lat is not None and loc_lon is not None:
                                popup_content = f"""
                                    <div style="font-size: 16px; font-family: Arial;">
                                    <b>{name}</b><br><br>
                                    <div style="font-size: 14px; font-family: Arial;">
                                    <b>Jangkauan radius geodesic:</b> {float(radius)} meter<br>
                                    <b>Jarak riil (OSRM):</b> {float(distance):.2f} meter<br>
                                    <b>Durasi riil (OSRM) :</b> {float(duration):.2f} menit<br>
                                    <b>Alamat:</b> {address}<br>
                                    <b>Fasilitas:</b> {fasilitas}<br>
                                    <b>Jam Operasi:</b> {loc.get('details', {}).get('jam_buka', '?')} - {loc.get('details', {}).get('jam_tutup', '?')}<br>
                                    <small>Lat: {loc_lat:.6f}, Lon: {loc_lon:.6f}</small>
                                    </div></div>
                                """

                                color_map = {
                                    1: "red",
                                    2: "blue",
                                    3: "green",
                                    4: "yellow"
                                }
                                if "Perdagangan" in name:
                                    circle = f'''
                                        <div style="
                                            width:20px;
                                            height:20px;
                                            background:{"black"};
                                            border-radius:50%;
                                            color:white;
                                            font-size:12px;
                                            line-height:20px;
                                            text-align:center;
                                            margin-top:0px;">
                                            {"Dg"}
                                        </div>
                                    '''

                                    icon = folium.DivIcon(
                                        html=f"""
                                        <div style="display:inline-block; text-align:center;">
                                            <div style="display:flex; justify-content:center; line-height:0;">
                                            </div>
                                            {circle}
                                        </div>
                                    """
                                    )
                                    folium.Marker(
                                        [float(loc_lat), float(loc_lon)],
                                        popup=folium.Popup(popup_content, max_width=500),
                                        icon=icon,
                                    ).add_to(locations_feature_group)
                                elif "Perikanan" in name:
                                    circle = f'''
                                        <div style="
                                            width:20px;
                                            height:20px;
                                            background:{"grey"};
                                            border-radius:50%;
                                            color:white;
                                            font-size:12px;
                                            line-height:20px;
                                            text-align:center;
                                            margin-top:0px;">
                                            {"Ik"}
                                        </div>
                                    '''

                                    icon = folium.DivIcon(
                                        html=f"""
                                        <div style="display:inline-block; text-align:center;">
                                            <div style="display:flex; justify-content:center; line-height:0;">
                                            </div>
                                            {circle}
                                        </div>
                                    """
                                    )
                                    folium.Marker(
                                        [float(loc_lat), float(loc_lon)],
                                        popup=folium.Popup(popup_content, max_width=500),
                                        icon=icon,
                                    ).add_to(locations_feature_group)
                                elif "Pertanian" in name:
                                    my_color = color_map[level]

                                    hair_boxes = ""
                                    for i in range(max(0, level)):
                                        # default rotasi 0
                                        angle = 0
                                        if level == 3:
                                            if i == 0:
                                                angle = -20
                                            elif i == 2:
                                                angle = 20
                                        hair_boxes += f'<div style="width:3px;height:8px;background:{my_color};' \
                                                      f'display:inline-block;margin:0 1px;transform:rotate({angle}deg);"></div>'

                                    # lingkaran utama dengan angka level
                                    circle = f'''
                                        <div style="
                                            width:20px;
                                            height:20px;
                                            background:{my_color};
                                            border-radius:50%;
                                            color:white;
                                            font-size:12px;
                                            line-height:20px;
                                            text-align:center;
                                            margin-top:0px;">
                                            {level}
                                        </div>
                                    '''

                                    icon = folium.DivIcon(
                                        html=f"""
                                            <div style="display:inline-block; text-align:center;">
                                                <div style="display:flex; justify-content:center; line-height:0;">
                                                    {hair_boxes}
                                                </div>
                                                {circle}
                                            </div>
                                        """
                                    )

                                    folium.Marker(
                                        location=[float(loc_lat), float(loc_lon)],
                                        icon=icon,
                                        popup=folium.Popup(popup_content, max_width=500),
                                    ).add_to(locations_feature_group)

                                # Simpan info untuk JS
                                marker_js_data.append({
                                    "lat": float(loc_lat),
                                    "lon": float(loc_lon),
                                    "name": name
                                })
                        except Exception as loc_error:
                            print(f"Error processing location {loc.get('id')}: {loc_error}")
                            continue
                    locations_feature_group.add_to(self.m)
                    folium.LayerControl().add_to(self.m)

                    right_click_js = """
                    <script>
                        document.addEventListener('DOMContentLoaded', function() {
                            setTimeout(function() {
                                const mapElement = document.querySelector('.folium-map');
                                const map = Object.values(window).find(
                                    (obj) => obj instanceof L.Map && obj.getContainer() === mapElement
                                );
                                if (!map) return;

                                let pusatMarker = null;

                                map.on('contextmenu', function(e) {
                                    e.originalEvent.preventDefault();
                                    if (e.latlng) {
                                        const { lat, lng } = e.latlng;

                                        // hapus marker lama jika ada
                                        if (pusatMarker) {
                                            map.removeLayer(pusatMarker);
                                        }

                                        var settings = {
                                          "url": "http://localhost:8000/location/pusat/update/",
                                          "method": "PUT",
                                          "timeout": 0,
                                          "headers": {
                                            "Content-Type": "application/json"
                                          },
                                          "data": JSON.stringify({
                                            "name": "TITIK PUSAT",
                                            "latitude": lat,
                                            "longitude": lng
                                          }),
                                        };

                                        $.ajax(settings).done(function (response) {
                                          console.log(response);
                                        });

                                        // buat marker baru
                                        pusatMarker = L.marker([lat, lng], {
                                            icon: L.icon({
                                                iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-icon.png',
                                                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-shadow.png',
                                                iconAnchor: [12, 41],
                                                popupAnchor: [1, -34]
                                            })
                                        }).addTo(map);

                                        // pasang popup dengan koordinat baru
                                        pusatMarker.bindPopup(
                                            `<div style="font-family: Arial, sans-serif; font-size: 16px;">
                                            <b>Titik Pusat telah diset di lokasi ini, silakan klik refresh kemudian OK!</b><br>Lat: ${lat.toFixed(6)}<br>Lon: ${lng.toFixed(6)}
                                            </div>`
                                        ).openPopup();
                                    }
                                });
                            }, 100);
                        });
                    </script>
                    """

                    click_route_js = f"""
                    <script>
                        function createBezierCurve(start, end, curvature = 0.3) {{
                            const midPoint = [
                                (start[0] + end[0]) / 2,
                                (start[1] + end[1]) / 2
                            ];

                            // Hitung control point untuk bezier curve
                            const dx = end[0] - start[0];
                            const dy = end[1] - start[1];

                            const controlPoint = [
                                midPoint[0] + dy * curvature,
                                midPoint[1] - dx * curvature
                            ];

                            // Generate points along the bezier curve
                            const curvePoints = [];
                            for (let t = 0; t <= 1; t += 0.05) {{
                                const x = Math.pow(1 - t, 2) * start[0] +
                                         2 * (1 - t) * t * controlPoint[0] +
                                         Math.pow(t, 2) * end[0];

                                const y = Math.pow(1 - t, 2) * start[1] +
                                         2 * (1 - t) * t * controlPoint[1] +
                                         Math.pow(t, 2) * end[1];

                                curvePoints.push([x, y]);
                            }}

                            return curvePoints;
                        }}

                        document.addEventListener('DOMContentLoaded', function() {{
                            setTimeout(function() {{
                                const mapElement = document.querySelector('.folium-map');
                                const map = Object.values(window).find(
                                    (obj) => obj instanceof L.Map && obj.getContainer() === mapElement
                                );
                                if (!map) return;

                                const centerLat = {lat};
                                const centerLon = {lon};
                                const markersData = {marker_js_data};

                                let activeLayers = []; // simpan semua layer aktif

                                function clearActiveLayers() {{
                                    activeLayers.forEach(layer => {{
                                        if (map.hasLayer(layer)) {{
                                            map.removeLayer(layer);
                                        }}
                                    }});
                                    activeLayers = [];
                                }}

                                markersData.forEach((m) => {{
                                    map.eachLayer((layer) => {{
                                        if (layer instanceof L.Marker) {{
                                            const pos = layer.getLatLng();
                                            if (pos.lat.toFixed(6) == m.lat.toFixed(6) && pos.lng.toFixed(6) == m.lon.toFixed(6)) {{
                                                layer.on('click', async function() {{
                                                    try {{
                                                        // Hapus semua layer lama
                                                        clearActiveLayers();

                                                        const url = `http://localhost:5000/route/v1/driving/${{centerLon}},${{centerLat}};${{m.lon}},${{m.lat}}?overview=full&geometries=geojson`;
                                                        const res = await fetch(url);
                                                        const data = await res.json();

                                                        if (data.routes && data.routes.length > 0) {{
                                                            const coords = data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
                                                            const distance = (data.routes[0].distance / 1000).toFixed(2);
                                                            const durationInSeconds = data.routes[0].duration;
                                                            const durationInMinutes = (durationInSeconds / 60).toFixed(1);

                                                            const clickedPoint = [m.lat, m.lon];
                                                            const endPoint = coords[coords.length - 1];
                                                            const bezierPoints = createBezierCurve(endPoint, clickedPoint, 0.5);

                                                            const beginPoint = [centerLat, centerLon];   
                                                            const startPoint = coords[0];                
                                                            const bezierPointsAwal = createBezierCurve(beginPoint, startPoint, 0.5);

                                                            // Buat polyline rute utama
                                                            const activeRoute = L.polyline(coords, {{
                                                                color: 'blue',
                                                                weight: 6,
                                                                opacity: 0.5
                                                            }}).addTo(map);
                                                            activeLayers.push(activeRoute);

                                                            // Titik awal
                                                            const activeStartCircle = L.circleMarker(coords[0], {{
                                                                radius: 6,
                                                                color: 'blue',
                                                                fillColor: 'white',
                                                                fillOpacity: .8
                                                            }}).addTo(map).bindPopup("Titik Awal");
                                                            activeLayers.push(activeStartCircle);

                                                            // Garis putus-putus
                                                            const dashedLinea = L.polyline(bezierPointsAwal, {{
                                                                color: 'blue',
                                                                weight: 4,
                                                                opacity: 0.6,
                                                                dashArray: '5, 7',
                                                                lineCap: 'round',
                                                                lineJoin: 'round',
                                                                className: 'dashed-connection-line'
                                                            }}).addTo(map);
                                                            activeLayers.push(dashedLinea);

                                                            // Titik akhir
                                                            const activeEndCircle = L.circleMarker(endPoint, {{
                                                                radius: 6,
                                                                color: 'blue',
                                                                fillColor: 'white',
                                                                fillOpacity: 0.8,
                                                                weight: 3
                                                            }}).addTo(map).bindPopup("Titik Akhir");
                                                            activeLayers.push(activeEndCircle);

                                                            // Garis putus-putus
                                                            const dashedLine = L.polyline(bezierPoints, {{
                                                                color: 'blue',
                                                                weight: 4,
                                                                opacity: 0.6,
                                                                dashArray: '5, 7',
                                                                lineCap: 'round',
                                                                lineJoin: 'round',
                                                                className: 'dashed-connection-line'
                                                            }}).addTo(map);
                                                            activeLayers.push(dashedLine);

                                                            // Label jarak & waktu
                                                            const midPoint = Math.floor(coords.length / 2);
                                                            const midCoord = coords[midPoint];

                                                            const distanceLabel = L.marker(midCoord, {{
                                                                icon: L.divIcon({{
                                                                    html: `<div style="
                                                                        padding: 3px;
                                                                        background: white;
                                                                        border: 2px solid blue;
                                                                        border-radius: 5px;
                                                                        padding: 2px 5px;
                                                                        font-weight: normal;
                                                                        font-size: 10px;
                                                                    ">
                                                                    <div style="
                                                                        display: flex;
                                                                        align-items: left;
                                                                        gap: 4px;
                                                                        padding: 3px 5px;
                                                                        background: white;
                                                                        font-weight: bold;
                                                                        font-size: 12px;
                                                                        line-height: 1;
                                                                    ">
                                                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="12"
                                                                         viewBox="0 0 64 64" fill="#231F20">
                                                                        <g>
                                                                            <path d="M43.293,18.696c0.195,0.195,0.451,0.293,0.707,0.293s0.512-0.098,0.707-0.293
                                                                                c0.391-0.391,0.391-1.023,0-1.414l-2-2c-0.391-0.391-1.023-0.391-1.414,0s-0.391,1.023,0,1.414L43.293,18.696z"/>
                                                                            <path d="M43.293,23.695c0.195,0.195,0.451,0.293,0.707,0.293s0.512-0.098,0.707-0.293
                                                                                c0.391-0.391,0.391-1.023,0-1.414l-7-7c-0.391-0.391-1.023-0.391-1.414,0s-0.391,1.023,0,1.414L43.293,23.695z"/>
                                                                            <g>
                                                                                <circle cx="11" cy="42.988" r="2"/>
                                                                                <path d="M58.982,32.076C58.985,32.045,59,32.02,59,31.988c0-2.866-0.589-28-21-28H26c-13.346,0-21,10.206-21,28
                                                                                    c0,0.031,0.015,0.057,0.018,0.088C2.176,32.547,0,35.016,0,37.988v10c0,3.309,2.691,6,6,6v5c0,0.553,0.447,1,1,1h8
                                                                                    c0.553,0,1-0.447,1-1v-5h32v5c0,0.553,0.447,1,1,1h8c0.553,0,1-0.447,1-1v-5c3.309,0,6-2.691,6-6v-10
                                                                                    C64,35.016,61.824,32.547,58.982,32.076z M14,57.988H8v-4h6V57.988z M11,46.988c-2.206,0-4-1.794-4-4s1.794-4,4-4
                                                                                    s4,1.794,4,4S13.206,46.988,11,46.988z M43,45.988H21c-0.553,0-1-0.447-1-1s0.447-1,1-1h22c0.553,0,1,0.447,1,1
                                                                                    S43.553,45.988,43,45.988z M18,31.988c0-3.313,2.687-6,6-6s6,2.687,6,6H18z M43,41.988H21c-0.553,0-1-0.447-1-1
                                                                                    s0.447-1,1-1h22c0.553,0,1,0.447,1,1S43.553,41.988,43,41.988z M32,31.988c0-4.418-3.582-8-8-8s-8,3.582-8,8h-5
                                                                                    c0-18.184,8.701-22,16-22h10c6.34,0,10.909,3.16,13.581,9.394C52.825,24.62,53,30.355,53,31.988H32z M56,57.988h-6v-4h6V57.988z
                                                                                     M53,46.988c-2.206,0-4-1.794-4-4s1.794-4,4-4s4,1.794,4,4S55.206,46.988,53,46.988z"/>
                                                                                <circle cx="53" cy="42.988" r="2"/>
                                                                            </g>
                                                                        </g>
                                                                    </svg>
                                                                    <span style="white-space: nowrap;">${{durationInMinutes}} min</span>
                                                                    </div>
                                                                    <div></div>
                                                                    <span style="margin-left: 5px; white-space: nowrap:">${{distance}} km</span>`,
                                                                    className: '',
                                                                    iconSize: [80, 40]
                                                                }}),
                                                                zIndexOffset: 1000,
                                                                interactive: false
                                                            }}).addTo(map);
                                                            activeLayers.push(distanceLabel);

                                                            map.fitBounds(activeRoute.getBounds());
                                                        }}
                                                    }} catch (err) {{
                                                        console.error("Gagal ambil rute:", err);
                                                    }}
                                                }});
                                            }}
                                        }}
                                    }});
                                }});
                            }}, 200);
                        }});
                    </script>
                    """

                    self.m.get_root().html.add_child(folium.Element(css_style))
                    self.m.get_root().html.add_child(folium.Element(right_click_js))
                    self.m.get_root().html.add_child(folium.Element(click_route_js))
                    self.add_legend()

                except requests.exceptions.RequestException as e:
                    QMessageBox.warning(self, "API Error", f"Gagal mengambil data: {str(e)}")

            # Simpan ke file HTML
            if not os.path.exists('temp'):
                os.makedirs('temp')
            map_path = os.path.join('temp', 'map.html')
            self.m.save(map_path)

            # Load peta di browser widget
            self.browser.setUrl(QUrl(f"http://localhost:{self.server_port}/temp/map.html"))

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Pastikan latitude dan longitude berupa angka")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Terjadi kesalahan: {str(e)}")

    def add_kecamatan(self):
        with open("geo_json/33.72_kecamatan.geojson", "r", encoding="utf-8") as f:
            data = json.load(f)

        folium.GeoJson(
            data,
            name="Batas Kecamatan",
            style_function=lambda feature: {

                "fillColor": "yellow",
                "color": "red",
                "weight": 2,
                "fillOpacity": 0.2,
            },
            tooltip=folium.GeoJsonTooltip(fields=["nm_kecamatan"], aliases=["Kecamatan:"])
        ).add_to(self.m)
        folium.LayerControl().add_to(self.m)

    def add_legend(self):
        """Menambahkan legenda ke peta"""
        legend_html = '''
        <div style="position: fixed;
                    bottom: 50px; left: 50px; width: 150px; height: 170px;
                    border:2px solid grey; z-index:9999; font-size:14px;
                    background-color:white;
                    padding:10px;">
          <b>Kategori Lokasi:</b><br>
          <i class="fa fa-star" style="color:red"></i> Titik Pusat <br>
          <i class="fa fa-map-marker" style="color:red"></i> Periode Tanam 1<br>
          <i class="fa fa-map-marker" style="color:blue"></i> Periode Tanam 2<br>
          <i class="fa fa-map-marker" style="color:green"></i> Periode Tanam 3<br>
          <i class="fa fa-map-marker" style="color:black"></i> Perdagangan<br>
          <i class="fa fa-map-marker" style="color:grey"></i> Perikanan<br>
        </div>
        '''
        self.m.get_root().html.add_child(folium.Element(legend_html))


class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
                border: none;
                background-color: #2c3e50;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgb(52, 73, 94);
            }
            QPushButton:checked {
                color: rgb(255, 255, 0);
            }
        """)


class SubMenuButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 30px;
                border: none;
                background-color: #2c3e50;
                color: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgb(52, 73, 94);
            }
            QPushButton:checked {
                color: rgb(255, 255, 0);
            }
        """)
        
class CircularImageLabel(QLabel):
    def __init__(self, image_url: str, diameter: int = 100, parent=None):
        super().__init__(parent)
        self._diameter = diameter
        self.setFixedSize(diameter, diameter)
        self.setPixmap(self._create_circular_pixmap(image_url, diameter))

    def _create_circular_pixmap(self, image_url: str, diameter: int) -> QPixmap:
        # 1) Load and scale the original pixmap (preserve aspect ratio, crop if needed)

        response = requests.get(image_url)
        img_data = response.content

        # Convert ke QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(img_data)

        src = pixmap
        if src.isNull():
            # fallback: empty transparent pixmap
            out = QPixmap(diameter, diameter)
            out.fill(Qt.transparent)
            return out

        # Scale so smaller side matches diameter, then we'll center-crop
        scaled = src.scaled(QSize(diameter, diameter), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        # 2) Prepare a transparent pixmap to draw the circular image into
        out = QPixmap(diameter, diameter)
        out.fill(Qt.transparent)

        # 3) Use QPainter with antialiasing and a circular clip path
        painter = QPainter(out)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, diameter, diameter)
        painter.setClipPath(path)

        # Compute top-left to center the scaled pixmap (because we used KeepAspectRatioByExpanding)
        x = (diameter - scaled.width()) // 2
        y = (diameter - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

        return out

    def setDiameter(self, diameter: int):
        self._diameter = diameter
        self.setFixedSize(diameter, diameter)

class MainWindow(QMainWindow):
    def __init__(self, login_window: QWidget):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1100, 650)
        self.settings = QSettings("Kho Ming Suun", "Geo Spatial")
        self.login_window = login_window

        defaults = {
            "last_keyword": "SMA",
            "last_lat": -7.557924,
            "last_lon": 110.786439,
            "last_layer": 1,
            "last_rad": 6000,
        }

        for key, value in defaults.items():
            if self.settings.value(key) is None:
                self.settings.setValue(key, value)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)

        # === Root layout ===
        self.root = QHBoxLayout()
        self.root.setContentsMargins(0,0,0,0)
        self.root.setSpacing(0)
        self.utb = QSITitleBar(self, '', False)
        self.main_layout.addWidget(self.utb)

        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)
        self.main_layout.addLayout(self.root)

        # === Sidebar ===
        self.sidebar_layout = QVBoxLayout()
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: #2c3e50; border: none;")
        self.scroll_widget = QWidget()
        self.scroll_widget.setLayout(self.sidebar_layout)
        self.scroll.setWidget(self.scroll_widget)
        self.scroll.setFixedWidth(230)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(110, 110, 110, 180))
        shadow.setOffset(3, 3)

        # === Header + Content Area ===
        main_area = QVBoxLayout()
        main_area.setContentsMargins(0, 0, 0, 0)
        main_area.setSpacing(0)

        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(0)

        # Tombol toggle sidebar
        self.btn_toggle_sidebar = QPushButton("☰")
        self.btn_toggle_sidebar.setFixedSize(30, 30)
        self.btn_toggle_sidebar.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                border: none;
                background-color: #bdc3c7;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)

        self.header_label = QLabel("GEO SEARCH", alignment=Qt.AlignCenter)
        self.header_label.setStyleSheet("""
                text-align: left;
                padding: 8px 30px;
                border: none;
                background-color: #34495e;
                color: white;
                font-size: 13px;
        """)

        header_bar.addWidget(self.btn_toggle_sidebar, alignment=Qt.AlignLeft)
        header_bar.addWidget(self.header_label, stretch=1)

        header_widget = QWidget()
        header_widget.setLayout(header_bar)
        header_widget.setContentsMargins(0,0,0,0)

        self.pages = QStackedWidget()
        self.pages.setStyleSheet("background-color: #ffffff;")

        # dict halaman
        self.pages_dict = {}
        def add_page(title):
            page = self.create_page(title)
            self.pages.addWidget(page)
            self.pages_dict[title] = page

        def add_titik_pusat():
            window = MapWidget()
            window.show()
            self.pages.addWidget(window)
            self.pages_dict["Tentukan Titik Pusat"] = window

            # Cleanup
            def cleanup():
                try:
                    import shutil
                    if os.path.exists('temp'):
                        shutil.rmtree('temp')
                except:
                    pass

        # add_page("Tentukan Titik Pusat")
        add_titik_pusat()
        add_page("Buat Geo location")
        add_page("Create Users")
        add_page("Users")
        add_page("Settings")
        # add_page("Logout")

        main_area.addWidget(header_widget)
        main_area.addWidget(self.pages)

        # === Sidebar Header ==

        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_layout = QHBoxLayout()

        logo = QLabel()
        pixmap = QPixmap("static/globe.svg")
        pixmap = pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pixmap)

        sidebar_hdr = QLabel("Admin Panel")
        sidebar_hdr.setMinimumSize(QSize(150, 48))
        sidebar_hdr.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sidebar_hdr.setStyleSheet("""
                    QLabel {
                        font-size: 18px;
                        border: none;
                        background-color: #2c3e50;
                    }
                """)
        sidebar_hdr.setGraphicsEffect(shadow)
        header_layout.addWidget(logo)
        header_layout.addWidget(sidebar_hdr)
        header_frame.setLayout(header_layout)

        # === Sidebar menu ===
        btn_maps = SidebarButton("📍  Maps")
        sub_maps = QVBoxLayout()
        btn_titik = SubMenuButton("Tentukan Titik Pusat")
        btn_geo = SubMenuButton("Buat Geo location")
        sub_maps.addWidget(btn_titik)
        sub_maps.addWidget(btn_geo)
        sub_maps_widget = QWidget()
        sub_maps_widget.setLayout(sub_maps)
        sub_maps_widget.setVisible(False)

        btn_maps.clicked.connect(lambda: sub_maps_widget.setVisible(not sub_maps_widget.isVisible()))
        btn_titik.clicked.connect(lambda: self.switch_page("Tentukan Titik Pusat"))
        btn_geo.clicked.connect(lambda: self.switch_page("Buat Geo location"))

        btn_users = SidebarButton("👤  Users")
        sub_users = QVBoxLayout()
        btn_create = SubMenuButton("Create Users")
        btn_list = SubMenuButton("Users")
        sub_users.addWidget(btn_create)
        sub_users.addWidget(btn_list)
        sub_users_widget = QWidget()
        sub_users_widget.setLayout(sub_users)
        sub_users_widget.setVisible(False)

        btn_users.clicked.connect(lambda: sub_users_widget.setVisible(not sub_users_widget.isVisible()))
        btn_create.clicked.connect(lambda: self.switch_page("Create Users"))
        btn_list.clicked.connect(lambda: self.switch_page("Users"))

        btn_settings = SidebarButton("⚙️  Settings")
        btn_logout = SidebarButton("🚪  Logout")
        btn_settings.clicked.connect(lambda: self.switch_page("Settings"))
        btn_logout.clicked.connect(lambda: self.handle_logout())

        profile_frame = QFrame()
        profile_frame.setFrameShape(QFrame.StyledPanel)

        profile_layout = QHBoxLayout()
        profile_layout.setAlignment(Qt.AlignCenter)

        img_url = self.settings.value("last_image_profile")
        profile_pic = CircularImageLabel(img_url, 36)
        profile_layout.addWidget(profile_pic)
        usr_name = self.settings.value("last_username")
        sidebar_user = QLabel(usr_name)
        sidebar_user.setMinimumSize(QSize(150, 40))
        sidebar_user.setAlignment(Qt.AlignVCenter)
        sidebar_user.setStyleSheet("""
                    QLabel {
                        font-size: 23px;
                        border: none;
                        background-color: #2c3e50;
                    }
                """)

        sidebar_user.setGraphicsEffect(shadow)

        # profile_layout.addWidget(profile_pic)
        profile_layout.addWidget(sidebar_user)
        profile_frame.setLayout(profile_layout)


        header_layout.addWidget(logo)
        header_layout.addWidget(sidebar_hdr)
        header_frame.setLayout(header_layout)


        self.sidebar_layout.addWidget(header_frame)
        self.sidebar_layout.addWidget(btn_maps)
        self.sidebar_layout.addWidget(sub_maps_widget)
        self.sidebar_layout.addWidget(btn_users)
        self.sidebar_layout.addWidget(sub_users_widget)
        self.sidebar_layout.addWidget(btn_settings)
        self.sidebar_layout.addStretch()
        self.sidebar_layout.addWidget(btn_logout)
        self.sidebar_layout.addWidget(profile_frame)

        group = QButtonGroup(self)
        group.setExclusive(True)
        group.addButton(btn_maps)
        group.addButton(btn_users)
        group.addButton(btn_titik)
        group.addButton(btn_geo)
        group.addButton(btn_create)
        group.addButton(btn_list)
        group.addButton(btn_settings)
        group.addButton(btn_logout)

        # === Gabungkan layout utama ===
        self.root.addWidget(self.scroll)
        self.root.addLayout(main_area)

        self.switch_page("Tentukan Titik Pusat")

    def create_page(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(title, alignment=Qt.AlignCenter)
        label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(label)
        return page

    def switch_page(self, name):
        if name in self.pages_dict:
            self.header_label.setText(name)
            self.pages.setCurrentWidget(self.pages_dict[name])

    def toggle_sidebar(self):
        """Hide/Show sidebar"""
        if self.scroll.isVisible():
            self.scroll.setVisible(False)
        else:
            self.scroll.setVisible(True)

    def handle_logout(self):
        # bersihkan QSettings kalau mau
        settings = QSettings("Kho Ming Suun", "Geo Spatial")
        settings.remove("last_token")

        self.login_window.show()
        self.close()

class LoginPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login Page")
        self.setMinimumSize(350, 200)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

        logo = QLabel()
        pixmap = QPixmap("static/geoinfo.png")
        pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setAlignment(Qt.AlignCenter)
        logo.setPixmap(pixmap)

        # === Form Layout ===
        form_layout = QFormLayout()
        form_layout.addRow(logo)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setText("lily")
        form_layout.addRow("Username:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText("secret123")
        form_layout.addRow("Password:", self.password_input)

        # === Button ===
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)

        # === Status Label ===
        self.status_label = QLabel("")

        # === Main Layout ===
        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addStretch()
        layout.addWidget(self.login_btn)
        layout.addWidget(self.status_label)
        self.center()

    def center(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    # def handle_login(self):
    #     username = self.username_input.text().strip()
    #     password = self.password_input.text().strip()
    #
    #     if not username or not password:
    #         self.status_label.setText("⚠️ Username and password required")
    #         return
    #
    #     url = "http://0.0.0.0:8000/token"
    #     payload = {
    #         "grant_type": "password",
    #         "username": username,
    #         "password": password,
    #         "scope": "",
    #         "client_id": "janus-client",
    #         "client_secret": "supersecret123",
    #     }
    #     headers = {"Accept": "application/json"}
    #     # str_json = None
    #     img_url = ""
    #     usr_name = ""
    #     try:
    #         response = requests.post(url, headers=headers, data=payload, timeout=5)
    #         response.raise_for_status()
    #         token_data = response.json()
    #         access_token = token_data.get("access_token")
    #         if access_token:
    #             url_me = "http://0.0.0.0:8000/me"
    #             headers = {
    #                 'Authorization': f"Bearer {access_token}",
    #             }
    #             response = requests.get(url_me, headers=headers)
    #             try:
    #                 str_json = json.loads(response.text)
    #                 img_url = str_json['image_profile']
    #                 usr_name = str_json['username']
    #             except json.JSONDecodeError as e:
    #                 print("Gagal parse JSON!")
    #                 print("Pesan error :", e.msg)
    #                 print("Posisi error:", e.pos)
    #
    #             settings = QSettings("Kho Ming Suun", "Geo Spatial")
    #             settings.setValue("last_token", f"Bearer {access_token}")
    #             settings.setValue("last_image_profile", img_url)
    #             settings.setValue("last_username", usr_name)
    #             main_window = MainWindow()
    #             main_window.show()
    #             self.close()
    #         else:
    #             self.status_label.setText("❌ Invalid response from server")
    #     except requests.exceptions.RequestException as e:
    #         self.status_label.setText(f"❌ Login failed: {e}")

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.status_label.setText("⚠️ Username and password required")
            return

        url = "http://0.0.0.0:8000/token"
        payload = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": "",
            "client_id": "janus-client",
            "client_secret": "supersecret123",
        }
        headers = {"Accept": "application/json"}

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=5)
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("access_token")
            if access_token:
                # --- ambil data user ---
                url_me = "http://0.0.0.0:8000/me"
                headers = {'Authorization': f"Bearer {access_token}"}
                response = requests.get(url_me, headers=headers)
                str_json = response.json()

                img_url = str_json.get("image_profile", "")
                usr_name = str_json.get("username", "")

                # --- simpan ke QSettings ---
                settings = QSettings("Kho Ming Suun", "Geo Spatial")
                settings.setValue("last_token", f"Bearer {access_token}")
                settings.setValue("last_image_profile", img_url)
                settings.setValue("last_username", usr_name)

                # --- buka MainWindow dengan referensi LoginWindow ---
                self.main_window = MainWindow(login_window=self)
                self.main_window.show()
                self.hide()  # jangan close, cukup sembunyikan
            else:
                self.status_label.setText("❌ Invalid response from server")
        except requests.exceptions.RequestException as e:
            self.status_label.setText(f"❌ Login failed: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginPage()
    login.show()
    sys.exit(app.exec())
