


<img width="1920" height="1920" alt="geoinfo" src="https://github.com/user-attachments/assets/36d3d249-38ee-467e-81b5-b2932ac307d8" />













# Geo Spatial Info

Adalah implementasi osrm pada osm maps (localhost) dideploy menggunakan docker backend. 
1. Osm (Open Street Maps) adalah layanan komunitas open source yang bergerak dibidang pemetaan.
2. Osrm (Open Street Route Maps) adalah jenis layanan lainnya yang berupa service routing antar titik-titik di dalam maps.

Download data dan backend dari penyedia osm + osrm, untuk dideploy di localhost kita, jadi layanan ini menjadi murni menggunakan koneksi LAN.

Berikut ini langkah download & install peta Indonesia:
### 1. Ambil data peta Indonesia
```
wget https://download.geofabrik.de/asia/indonesia-latest.osm.pbf
```
### 2. Pull image OSRM sekali saja
```
docker pull osrm/osrm-backend
```
### 3. Extract peta
```
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/indonesia-latest.osm.pbf
```
### 4. Partition
```
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/indonesia-latest.osrm
```
### 5. Customize
```
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/indonesia-latest.osrm
```
## 6. Jalankan server di port 5000
```
docker run -t -i -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/indonesia-latest.osrm
```

Aplikasi ini dapat menentukan sebuah titik geo location di dalam maps kemudian memberi spesifikasi tertentu dan menyimpannya dalam database, dengan begitu titik-titik geo location dapat digolongkan sesuai dengan kondisi kesamaan yang spesifik sebagai contoh:
1. Lahan pertanian
2. Pusat perikanan
3. Pusat dagang
   
Pada akhirnya end user dapat melakukan filter informasi agar sesuai dengan yang dibutuhkan. Pencarian geo location juga dapat ditentukan pula oleh kedekatan dengan “TITIK PUSAT” digolongkan 2 jenis:
1. Jarak riil diukur dengan fitur route yang dimiliki OSRM ini meliputi:
   
   a.  Jarak dalam km
   
   b.  Waktu tempuh dalam menit
   
3. Radius ukuran geodesic, diukur dari titik pusat dengan garis lurus sejauh radius ke lingkaran terluar


Implementasi rute antar dua titik menggunakan OSRM, rute akan digambar dengan default driving mode (sementara hanya ini service tersedia), diujung rute sudah terdapat bezier curve, ini untuk menjelaskan bahwa jalan terakhir yang bisa ditempuh melalui mobil dihubungkan dengan bezier curve putus-putus ke titik pusat maupun titik lokasi.

Implementasi beberapa layer kedalam maps untuk mendukung penyajian data yang lebih aktual termasuk layer area seperti geoJson layer untuk menampilkan wilayah
tertentu contohnya area kota dibagi beberapa kecamatan akan dimunculkan dalam gambar berupa garis batas kota maupun batas kecamatannya, contohnya:
1. Esri
2. Open street maps
3. Satelite view
4. Radius geodesic

Terdapat penangan khusus terhadap data pertanian, user dapat melakukan filter terhadap status kondisi lahan yaitu periode tanam sebuah lahan
1. Periode tanam 1 (p1: misalkan dihitung 10 hari setelah tanam)
2. Periode tanam 2 (p2: 20 hari setelah tanam)
3. Periode tanam 3 (p3: 40 hari setelah tanam sampai menjelang panen)
