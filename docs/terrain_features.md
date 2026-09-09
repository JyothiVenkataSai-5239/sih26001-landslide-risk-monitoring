# Terrain Features (Sikkim Pilot Region) — Technical Documentation

Documentation of the geodetic terrain features derived from the NASA SRTM GL1 Digital Elevation Model (DEM) in **Step 3C**.

---

## 1. Input Data Overview

- **DEM Source:** NASA / USGS Shuttle Radar Topography Mission (SRTM) Global 1 Arc-Second (~30 m resolution).
- **Input DEM File Path:** `data/raw/dem/extracted/output_SRTMGL1.tif`
- **Coordinate Reference System (CRS):** `EPSG:4326` (WGS 84 geographic latitude/longitude).
- **Native Resolution:** `0.000277777777778°` × `0.000277777777778°` (1 arc-second).
- **Spatial Dimensions:** `3,960` columns × `3,240` rows (`12,830,400` total pixels).
- **Spatial Bounds:**
  - West (Left): `87.899861° E`
  - East (Right): `88.999861° E`
  - South (Bottom): `27.000139° N`
  - North (Top): `27.900139° N`

---

## 2. Geodesic Metric Scaling Methodology

Because the DEM is referenced in geographic angular coordinates (`EPSG:4326` degrees), degrees cannot simply be treated as meters when computing horizontal surface gradients.

To ensure exact spatial derivatives, ground spacing was computed per row across the **WGS 84 Reference Ellipsoid** ($a = 6,378,137.0\text{ m}$, $e^2 = 0.00669437999014$):

$$\phi_r = \text{Latitude at row } r$$

1. **Meridional distance per pixel ($dy$ in meters):**
   $$M(\phi_r) = \frac{a(1 - e^2)}{(1 - e^2 \sin^2 \phi_r)^{1.5}}$$
   $$dy(\phi_r) = M(\phi_r) \cdot \Delta \phi_{\text{rad}} \approx 30.779\text{ m to } 30.783\text{ m}$$

2. **Parallel distance per pixel ($dx$ in meters):**
   $$N(\phi_r) = \frac{a}{\sqrt{1 - e^2 \sin^2 \phi_r}}$$
   $$dx(\phi_r) = N(\phi_r) \cos(\phi_r) \cdot \Delta \lambda_{\text{rad}} \approx 27.348\text{ m to } 27.571\text{ m}$$

Both $dx$ and $dy$ were dynamically computed as latitude-dependent arrays broadcast across the 2D elevation grid.

---

## 3. Terrain Derivatives & Mathematical Formulations

### A. Elevation (`elevation.tif`)

- **Method:** Extracted directly from the validated DEM array.
- **Unit:** Meters ($m$) above sea level.
- **Statistics:**
  - Min: `182.0000 m`
  - Max: `8,376.0000 m`
  - Mean: `3,188.8084 m`
  - Std: `1,586.8269 m`

---

### B. Slope (`slope.tif`)

- **Method:** Horn (1981) 3×3 weighted finite-difference convolution kernel:
  $$p = \frac{\partial z}{\partial x} = \frac{(z_3 + 2z_6 + z_9) - (z_1 + 2z_4 + z_7)}{8 \cdot dx}$$
  $$q = \frac{\partial z}{\partial y} = \frac{(z_1 + 2z_2 + z_3) - (z_7 + 2z_8 + z_9)}{8 \cdot dy}$$
  $$\text{Slope}_{\text{rad}} = \arctan\left(\sqrt{p^2 + q^2}\right)$$
  $$\text{Slope}_{\text{deg}} = \text{Slope}_{\text{rad}} \times \frac{180}{\pi}$$
- **Unit:** Degrees ($^\circ$), ranging from $0^\circ$ (flat) to $90^\circ$ (vertical).
- **Statistics:**
  - Min: `0.0000°`
  - Max: `87.0707°`
  - Mean: `28.7377°`
  - Std: `12.0453°`

---

### C. Aspect (`aspect.tif`)

- **Method:** Compass downhill azimuth of steepest descent.
  The downhill descent direction vector is $(v_x, v_y) = (-p, -q)$.
  $$\text{Azimuth} = \text{atan2}(-p, -q) \times \frac{180}{\pi} \pmod{360}$$
  Standard cartographic convention:
  - $0^\circ$: North
  - $90^\circ$: East
  - $180^\circ$: South
  - $270^\circ$: West
  - Flat surfaces ($\text{Slope} < 0.1^\circ$) are assigned `-1.0` (standard GDAL/ArcGIS flat designation).
- **Unit:** Degrees ($0^\circ \le \text{Aspect} < 360^\circ$; flat = $-1$).
- **Statistics (Non-flat surfaces):**
  - Min: `0.0000°`
  - Max: `359.9272°`
  - Mean: `179.7247°`
  - Std: `107.3590°`

---

### D. Curvature (`curvature.tif`)

- **Method:** Zevenbergen & Thorne (1987) / surface Laplacian:
  $$\frac{\partial^2 z}{\partial x^2} = \frac{z_{i, j-1} - 2z_{i,j} + z_{i, j+1}}{dx^2}$$
  $$\frac{\partial^2 z}{\partial y^2} = \frac{z_{i-1, j} - 2z_{i,j} + z_{i+1, j}}{dy^2}$$
  $$\text{Curvature} = -\left(\frac{\partial^2 z}{\partial x^2} + \frac{\partial^2 z}{\partial y^2}\right) \times 100$$
  - Positive values ($> 0$): Surface is upwardly convex (ridges, crests, shedding slopes).
  - Negative values ($< 0$): Surface is upwardly concave (valleys, ravines, convergent flow channels).
  - Zero ($= 0$): Planar / uniform linear slope.
- **Unit:** $100 \times m^{-1}$ ($m / 100m^2$).
- **Statistics:**
  - Min: `-590.4033` (deep narrow valleys / gullies)
  - Max: `253.6031` (sharp ridges / mountain peaks)
  - Mean: `-0.0000` (balanced terrain morphology)
  - Std: `2.1248`

---

## 4. Generated Artifacts

| Layer            | File Path                                     | Format  | Dimensions  | Data Type | NoData  |
| :--------------- | :-------------------------------------------- | :------ | :---------- | :-------- | :------ |
| **Elevation**    | `data/processed/terrain/elevation.tif`        | GeoTIFF | 3960 × 3240 | Float32   | -9999.0 |
| **Slope**        | `data/processed/terrain/slope.tif`            | GeoTIFF | 3960 × 3240 | Float32   | -9999.0 |
| **Aspect**       | `data/processed/terrain/aspect.tif`           | GeoTIFF | 3960 × 3240 | Float32   | -9999.0 |
| **Curvature**    | `data/processed/terrain/curvature.tif`        | GeoTIFF | 3960 × 3240 | Float32   | -9999.0 |
| **Summary JSON** | `data/processed/terrain/terrain_summary.json` | JSON    | —           | —         | —       |

---

## 5. Verification & Coverage Results

- **Raster Dimensions:** Exactly consistent across all 4 layers (3,960 × 3,240).
- **Coordinate Reference System:** `EPSG:4326` preserved across all layers.
- **Data Completeness:** 100% valid data (`12,830,400` pixels), zero unexpected empty or corrupted pixels.
- **Cross-Validation with Landslide Inventory:** All **777 of 777 (100%)** historical landslide occurrence records in `data/processed/landslides/sikkim_landslides.csv` fall strictly within the spatial bounds of these terrain layers.
