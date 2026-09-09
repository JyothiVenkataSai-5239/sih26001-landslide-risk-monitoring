import React, { useEffect, useState, useRef, useMemo } from 'react'
import { MapContainer, TileLayer, CircleMarker, Marker, Popup, Polygon } from 'react-leaflet'
import L from 'leaflet'
import axios from 'axios'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

import iconUrl from 'leaflet/dist/images/marker-icon.png'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

// Sikkim geographic bounds & view parameters with surrounding context
const SIKKIM_CENTER = [27.50, 88.50]
const SIKKIM_BOUNDS = [
  [26.85, 87.80], // South-West bound (Nepal & West Bengal margin for geographic context)
  [28.25, 89.15], // North-East bound (Tibet & Bhutan margin for geographic context)
]
const MIN_ZOOM = 8   // Prevents zooming out to broad India / world view
const MAX_ZOOM = 16  // Allows high-resolution corridor zoom
const DEFAULT_ZOOM = 9.5
const AUTO_REFRESH_INTERVAL_MS = 60000 // 60-second auto-refresh polling interval

// Subtle Sikkim State border outline coordinates
const SIKKIM_BORDER_RING = [
  [27.04, 88.42], // Melli / Teesta border
  [27.06, 88.26], // Jorethang / South-West
  [27.12, 88.13], // Singalila Ridge
  [27.20, 88.07], // West Sikkim / Nepal border
  [27.32, 88.05], // Uttarey / West border
  [27.45, 88.08], // Dzongri / Kanchenjunga base
  [27.60, 88.11], // Kanchenjunga massif
  [27.75, 88.15], // North-West border
  [27.88, 88.20], // Lhonak valley
  [27.98, 88.32], // Muguthang
  [28.08, 88.50], // Dongkha La / Northern apex
  [28.14, 88.62], // Pauhunri apex
  [28.06, 88.75], // Gurudongmar / North-East
  [27.92, 88.84], // Chho Lhamo
  [27.78, 88.82], // East Sikkim border
  [27.60, 88.80], // Kupup
  [27.42, 88.82], // Nathu La pass
  [27.32, 88.88], // Jelep La pass
  [27.18, 88.76], // Rongli / East border
  [27.10, 88.58], // Rorathang / South-East
  [27.05, 88.46], // Teesta confluence
  [27.04, 88.42], // Closing point
]

// Fix Leaflet's default icon paths when bundlers change asset locations
L.Icon.Default.mergeOptions({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
})

function riskColor(tier) {
  if (!tier && typeof tier !== 'number') return '#6b7280'
  if (typeof tier === 'string') {
    const v = tier.toLowerCase()
    if (v.includes('very')) return '#EF4444'
    if (v.includes('high')) return '#F97316'
    if (v.includes('moderate')) return '#F59E0B'
    return '#10B981'
  }
  const s = Number(tier)
  if (isNaN(s)) return '#6b7280'
  if (s >= 0.8) return '#EF4444'
  if (s >= 0.6) return '#F97316'
  if (s >= 0.4) return '#F59E0B'
  return '#10B981'
}

// Clean, lightweight CircleMarker styling for individual risk cells: radius: 4px, fillOpacity: 0.8
function getGridMarkerStyle(tier) {
  const t = (tier || '').toString().toUpperCase()
  if (t.includes('VERY')) {
    return {
      fillColor: '#EF4444',
      fillOpacity: 0.8,
      color: '#EF4444',
      weight: 0.5,
      radius: 4,
    }
  }
  if (t.includes('HIGH')) {
    return {
      fillColor: '#F97316',
      fillOpacity: 0.8,
      color: '#F97316',
      weight: 0.5,
      radius: 4,
    }
  }
  if (t.includes('MODERATE')) {
    return {
      fillColor: '#F59E0B',
      fillOpacity: 0.8,
      color: '#F59E0B',
      weight: 0.5,
      radius: 4,
    }
  }
  // LOW
  return {
    fillColor: '#10B981',
    fillOpacity: 0.8,
    color: '#10B981',
    weight: 0.5,
    radius: 4,
  }
}

function isValidLatLon(lat, lon) {
  if (typeof lat !== 'number' || typeof lon !== 'number') return false
  if (!isFinite(lat) || !isFinite(lon)) return false
  if (lat < -90 || lat > 90) return false
  if (lon < -180 || lon > 180) return false
  return true
}

export default function MapView() {
  const [coarse, setCoarse] = useState([])
  const [fine, setFine] = useState([]) // separate fine grid state
  const [hotspots, setHotspots] = useState([])
  const [alerts, setAlerts] = useState([])
  const [forecast, setForecast] = useState([])
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const [backendOnline, setBackendOnline] = useState(true)

  const [showRisk, setShowRisk] = useState(true)
  const [showHotspots, setShowHotspots] = useState(true)
  const [showAlerts, setShowAlerts] = useState(true)

  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [selectedHorizon, setSelectedHorizon] = useState('+6h')

  // Step 18: Risk Inspector
  const [selectedRiskLocation, setSelectedRiskLocation] = useState(null)
  const [showInspector, setShowInspector] = useState(false)
  const [shapData, setShapData] = useState(null)
  const [inspectorLoading, setInspectorLoading] = useState(false)

  const mapRef = useRef(null)
  const hasFittedBounds = useRef(false)

  const fetchAll = async (isBackground = false) => {
    if (!isBackground) setLoading(true)
    setIsRefreshing(true)
    setError(null)
    const base = 'http://127.0.0.1:8000'
    const safe = (arr) => Array.isArray(arr) ? arr : []

    try {
      const results = await Promise.allSettled([
        axios.get(`${base}/api/risk/coarse?sample_step=10`),
        axios.get(`${base}/api/risk/fine?limit=500`),
        axios.get(`${base}/api/forecast?sample_step=10`),
        axios.get(`${base}/api/hotspots`),
        axios.get(`${base}/api/alerts`),
      ])

      const [cRes, fRes, fcRes, hRes, aRes] = results
      let successCount = 0

      // 1. Coarse Risk Grid
      if (cRes.status === 'fulfilled') {
        const parsedCoarse = safe(cRes.value.data).map((r, i) => {
          const lat = parseFloat(r.latitude ?? r.lat ?? r.lat_dd ?? NaN)
          const lon = parseFloat(r.longitude ?? r.lon ?? r.lng ?? NaN)
          return ({
            ...r,
            _lat: isFinite(lat) ? lat : null,
            _lon: isFinite(lon) ? lon : null,
            _key: r.cell_id ?? r.id ?? `coarse_${i}`,
          })
        }).filter(x => x._lat !== null && x._lon !== null && isValidLatLon(x._lat, x._lon))
        if (parsedCoarse.length > 0) {
          setCoarse(parsedCoarse)
        }
        successCount++
      } else {
        console.warn('Failed to load coarse grid during refresh (preserving previous):', cRes.reason?.message)
      }

      // 2. Fine Risk Grid
      if (fRes.status === 'fulfilled') {
        const parsedFine = safe(fRes.value.data).map((f, i) => {
          const lat = parseFloat(f.latitude ?? f.lat ?? NaN)
          const lon = parseFloat(f.longitude ?? f.lon ?? f.lng ?? NaN)
          return ({
            ...f,
            _lat: isFinite(lat) ? lat : null,
            _lon: isFinite(lon) ? lon : null,
            _key: f.fine_cell_id ?? f.cell_id ?? f.id ?? `fine_${i}`,
          })
        }).filter(x => x._lat !== null && x._lon !== null && isValidLatLon(x._lat, x._lon))
        if (parsedFine.length > 0) {
          setFine(parsedFine)
        }
        successCount++
      } else {
        console.warn('Failed to load fine grid during refresh (preserving previous):', fRes.reason?.message)
      }

      // 3. Multi-horizon Forecast Grid
      if (fcRes.status === 'fulfilled') {
        const parsedForecast = safe(fcRes.value.data).map((f, i) => {
          const lat = parseFloat(f.latitude ?? f.lat ?? NaN)
          const lon = parseFloat(f.longitude ?? f.lon ?? f.lng ?? NaN)
          return ({
            ...f,
            _lat: isFinite(lat) ? lat : null,
            _lon: isFinite(lon) ? lon : null,
            _key: f.cell_id ?? f.id ?? `forecast_${i}`,
          })
        })
        if (parsedForecast.length > 0) {
          setForecast(parsedForecast)
        }
        successCount++
      } else {
        console.warn('Failed to load forecast grid during refresh (preserving previous):', fcRes.reason?.message)
      }

      // 4. Infrastructure Corridor Hotspots
      if (hRes.status === 'fulfilled') {
        const parsedHotspots = safe(hRes.value.data).map((s, i) => {
          const lat = parseFloat(s.latitude ?? s.lat ?? NaN)
          const lon = parseFloat(s.longitude ?? s.lon ?? s.lng ?? NaN)
          return ({
            ...s,
            _lat: isFinite(lat) ? lat : null,
            _lon: isFinite(lon) ? lon : null,
            _key: s.station_id ? `${s.station_id}_${s.forecast_horizon ?? i}` : (s.id ?? `hs_${i}`),
          })
        }).filter(x => x._lat !== null && x._lon !== null && isValidLatLon(x._lat, x._lon))
        if (parsedHotspots.length > 0) {
          setHotspots(parsedHotspots)
        }
        successCount++
      } else {
        console.warn('Failed to load hotspots during refresh (preserving previous):', hRes.reason?.message)
      }

      // 5. Active Alerts
      if (aRes.status === 'fulfilled') {
        const parsedAlerts = safe(aRes.value.data).map((a, i) => {
          const lat = parseFloat(a.latitude ?? a.lat ?? NaN)
          const lon = parseFloat(a.longitude ?? a.lon ?? a.lng ?? NaN)
          return ({
            ...a,
            _lat: isFinite(lat) ? lat : null,
            _lon: isFinite(lon) ? lon : null,
            _key: a.alert_id ?? a.id ?? `alert_${i}`,
          })
        }).filter(x => x._lat !== null && x._lon !== null && isValidLatLon(x._lat, x._lon))
        if (parsedAlerts.length > 0) {
          setAlerts(parsedAlerts)
        }
        successCount++
      } else {
        console.warn('Failed to load alerts during refresh (preserving previous):', aRes.reason?.message)
      }

      if (successCount > 0) {
        setBackendOnline(true)
        const now = new Date()
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
        setLastUpdated(`${timeStr}`)
        setError(null)
      } else {
        setBackendOnline(false)
        setError('Backend unreachable — displaying last loaded monitoring data.')
      }
    } catch (err) {
      setError(err.message || 'API error')
      setBackendOnline(false)
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }

  // Initial load and periodic automatic refresh
  useEffect(() => {
    fetchAll(false)
    const interval = setInterval(() => {
      fetchAll(true)
    }, AUTO_REFRESH_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [])

  // Load SHAP data for explainability
  useEffect(() => {
    const loadShapData = async () => {
      try {
        const res = await axios.get('http://127.0.0.1:8000/explainability/shap-summary')
        setShapData(res.data)
      } catch (err) {
        console.warn('SHAP data unavailable:', err.message)
        setShapData(null)
      }
    }
    loadShapData()
  }, [])

  // Auto-fit map to Sikkim on initial load only (never re-centers on auto-refresh)
  useEffect(() => {
    if (!hasFittedBounds.current && mapRef.current && (coarse.length > 0 || hotspots.length > 0)) {
      try {
        const bounds = L.latLngBounds(SIKKIM_BOUNDS)
        mapRef.current.fitBounds(bounds, { padding: [20, 20] })
        hasFittedBounds.current = true
      } catch (e) {
        // silent
      }
    }
  }, [coarse, hotspots])

  const hotspotIcon = new L.Icon({
    iconUrl: iconUrl,
    iconRetinaUrl: iconRetinaUrl,
    shadowUrl: shadowUrl,
    iconSize: [24, 38],
    iconAnchor: [12, 38],
  })

  const alertIcon = new L.DivIcon({
    className: 'custom-alert-icon',
    html: '<div style="background:#EF4444;width:14px;height:14px;border-radius:7px;border:2px solid #fff"></div>',
    iconSize: [18, 18],
    iconAnchor: [9, 9]
  })

  const centerAndZoom = (lat, lon, zoom = 13) => {
    try {
      const map = mapRef.current
      if (map && map.setView) map.setView([lat, lon], zoom)
    } catch (e) {
      // ignore
    }
  }

  const filteredAlerts = alerts.filter(a => {
    if (severityFilter === 'ALL') return true
    const sev = (a.alert_severity || a.severity || '').toString().toUpperCase()
    return sev.includes(severityFilter)
  })

  // KPI Calculations
  const totalCells = coarse.length
  const highRiskCells = coarse.filter(c => {
    const tier = (c.risk_tier || '').toString().toUpperCase()
    return tier.includes('HIGH') && !tier.includes('VERY')
  }).length
  const veryHighRiskCells = coarse.filter(c => {
    const tier = (c.risk_tier || '').toString().toUpperCase()
    return tier.includes('VERY')
  }).length
  const activeAlerts = alerts.filter(a => {
    const status = (a.status || a.alert_status || '').toString().toUpperCase()
    return status.includes('ACTIVE')
  }).length
  const maxRisk = coarse.length > 0 ? Math.max(...coarse.map(c => parseFloat(c.risk_score ?? 0) || 0)).toFixed(3) : 'N/A'

  // Risk distribution chart data
  const riskDistribution = (() => {
    const counts = { LOW: 0, MODERATE: 0, HIGH: 0, VERY_HIGH: 0 }
    coarse.forEach(c => {
      const tier = (c.risk_tier || '').toString().toUpperCase()
      if (tier.includes('VERY')) counts.VERY_HIGH++
      else if (tier.includes('HIGH')) counts.HIGH++
      else if (tier.includes('MODERATE')) counts.MODERATE++
      else counts.LOW++
    })
    return [
      { name: 'LOW', count: counts.LOW, fill: '#10B981' },
      { name: 'MODERATE', count: counts.MODERATE, fill: '#F59E0B' },
      { name: 'HIGH', count: counts.HIGH, fill: '#F97316' },
      { name: 'VERY HIGH', count: counts.VERY_HIGH, fill: '#EF4444' }
    ]
  })()

  // Layered coarse grid sorted by risk tier so HIGH/VERY HIGH render cleanly on top
  const sortedCoarse = useMemo(() => {
    const tierPriority = (tier) => {
      const t = (tier || '').toString().toUpperCase()
      if (t.includes('VERY')) return 4
      if (t.includes('HIGH')) return 3
      if (t.includes('MODERATE')) return 2
      return 1
    }
    return [...coarse].sort((a, b) => tierPriority(a.risk_tier) - tierPriority(b.risk_tier))
  }, [coarse])

  // Forecast statistics for selected horizon
  const horizonKey = `risk_${selectedHorizon}`
  const tierKey = `tier_${selectedHorizon}`
  const forecastStats = (() => {
    const validForecasts = forecast.filter(f => f[horizonKey] !== undefined && f[horizonKey] !== null)
    if (validForecasts.length === 0) return { max: 'N/A', avg: 'N/A', highCount: 0, veryHighCount: 0 }
    
    const risks = validForecasts.map(f => parseFloat(f[horizonKey]) || 0)
    const max = Math.max(...risks).toFixed(3)
    const avg = (risks.reduce((a, b) => a + b, 0) / risks.length).toFixed(3)
    let highCount = 0, veryHighCount = 0
    validForecasts.forEach(f => {
      const tier = (f[tierKey] || '').toString().toUpperCase()
      if (tier.includes('VERY')) veryHighCount++
      else if (tier.includes('HIGH')) highCount++
    })
    return { max, avg, highCount, veryHighCount }
  })()

  // Top hotspots by risk
  const topHotspots = (() => {
    return hotspots
      .filter(h => h.forecast_risk_score !== undefined && h.forecast_risk_score !== null)
      .sort((a, b) => (parseFloat(b.forecast_risk_score) || 0) - (parseFloat(a.forecast_risk_score) || 0))
      .slice(0, 5)
  })()

  // Step 18: Risk Inspector functions
  const openRiskInspector = (riskData) => {
    setSelectedRiskLocation(riskData)
    setShowInspector(true)
  }

  const generateExplanation = () => {
    if (!shapData || !shapData.global_features) {
      return 'Detailed local explanation unavailable for this location.'
    }
    
    const topFeatures = shapData.global_features.slice(0, 3).map(f => f.feature.toLowerCase())
    if (topFeatures.length === 0) {
      return 'Detailed local explanation unavailable for this location.'
    }
    
    return `Risk is elevated mainly because of the model's association with ${topFeatures.join(', ')} and terrain characteristics. Model-based explanation — not causal proof.`
  }

  const getRiskProfile = () => {
    if (!selectedRiskLocation) return null
    const loc = selectedRiskLocation
    return {
      susceptibility: (loc.susceptibility_score ?? loc.susceptibility ?? 'N/A'),
      rainfall: (loc.rainfall_trigger_index ?? loc.r_idx ?? 'N/A'),
      riskScore: (loc.risk_score ?? loc.risk ?? 'N/A'),
      riskTier: (loc.risk_tier ?? loc.risk_category ?? 'N/A'),
    }
  }

  return (
    <div className="map-shell text-white bg-gray-900 flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="w-full flex-shrink-0 flex items-center justify-between p-3 bg-black bg-opacity-80 z-20 border-b border-gray-700">
        <div className="pl-2">
          <div className="text-lg font-bold">🗺️ Sikkim Landslide Early Warning System</div>
          <div className="text-xs text-gray-300">Command Center | Professional Risk Analytics</div>
        </div>
        <div className="pr-4 flex items-center space-x-3">
          {lastUpdated && (
            <div className="text-xs text-gray-300 hidden sm:flex items-center gap-1.5 bg-gray-800 bg-opacity-80 px-2.5 py-1 rounded border border-gray-700">
              <span className="text-gray-400">🕒 Last Updated:</span>
              <span className="font-mono text-cyan-300 font-semibold">{lastUpdated}</span>
            </div>
          )}
          {isRefreshing && (
            <span className="text-xs text-blue-400 font-semibold animate-pulse flex items-center gap-1">
              <span className="animate-spin inline-block">↻</span> Syncing...
            </span>
          )}
          <div className={`px-3 py-1 text-xs rounded font-semibold ${backendOnline ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
            {backendOnline ? '🟢 ONLINE' : '🔴 OFFLINE'}
          </div>
          <button 
            onClick={() => fetchAll(false)} 
            disabled={isRefreshing}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1 rounded text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <span className={isRefreshing ? 'animate-spin inline-block' : ''}>↻</span>
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </header>

      {/* Main 3-Column Layout */}
      <div className="flex flex-1 min-h-0 gap-2 p-2 overflow-hidden">
        
        {/* LEFT SIDEBAR - 20% */}
        <div className="w-1/5 min-h-0 h-full bg-black bg-opacity-60 rounded border border-gray-700 p-3 overflow-y-auto flex flex-col gap-4">
          <div>
            <div className="text-sm font-bold mb-2 text-blue-300">📊 Key Performance Indicators</div>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-gray-800 rounded p-2 text-center border border-gray-700">
                <div className="text-xs text-gray-300">Total Cells</div>
                <div className="text-xl font-bold text-white">{totalCells}</div>
              </div>
              <div className="bg-gray-800 rounded p-2 text-center border border-gray-700">
                <div className="text-xs text-gray-300">HIGH Risk</div>
                <div className="text-xl font-bold text-orange-400">{highRiskCells}</div>
              </div>
              <div className="bg-gray-800 rounded p-2 text-center border border-gray-700">
                <div className="text-xs text-gray-300">VERY HIGH</div>
                <div className="text-xl font-bold text-red-400">{veryHighRiskCells}</div>
              </div>
              <div className="bg-gray-800 rounded p-2 text-center border border-gray-700">
                <div className="text-xs text-gray-300">Active Alerts</div>
                <div className="text-xl font-bold text-yellow-300">{activeAlerts}</div>
              </div>
            </div>
            <div className="bg-gray-800 rounded p-2 text-center border border-gray-700 mt-2 flex justify-between items-center px-3">
              <div className="text-left">
                <div className="text-xs text-gray-400">Max Risk Score</div>
                <div className="text-base font-bold text-red-300">{maxRisk}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-400">Last Sync</div>
                <div className="text-xs font-mono text-cyan-300">{lastUpdated || 'Initial load...'}</div>
              </div>
            </div>
          </div>

          {/* Risk Legend */}
          <div>
            <div className="text-sm font-bold mb-2 text-green-300">🎨 Risk Legend</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2"><span className="w-4 h-4 rounded" style={{background:'#10B981'}}></span><span>LOW</span></div>
              <div className="flex items-center gap-2"><span className="w-4 h-4 rounded" style={{background:'#F59E0B'}}></span><span>MODERATE</span></div>
              <div className="flex items-center gap-2"><span className="w-4 h-4 rounded" style={{background:'#F97316'}}></span><span>HIGH</span></div>
              <div className="flex items-center gap-2"><span className="w-4 h-4 rounded" style={{background:'#EF4444'}}></span><span>VERY HIGH</span></div>
            </div>
          </div>

          {/* Layer Controls */}
          <div>
            <div className="text-sm font-bold mb-2 text-cyan-300">🔳 Layers</div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <input id="rl" type="checkbox" checked={showRisk} onChange={() => setShowRisk(!showRisk)} className="cursor-pointer"/>
                <label htmlFor="rl" className="cursor-pointer">Risk Grid</label>
              </div>
              <div className="flex items-center gap-2">
                <input id="hs" type="checkbox" checked={showHotspots} onChange={() => setShowHotspots(!showHotspots)} className="cursor-pointer"/>
                <label htmlFor="hs" className="cursor-pointer">Hotspot Corridors</label>
              </div>
              <div className="flex items-center gap-2">
                <input id="al" type="checkbox" checked={showAlerts} onChange={() => setShowAlerts(!showAlerts)} className="cursor-pointer"/>
                <label htmlFor="al" className="cursor-pointer">Active Alerts</label>
              </div>
            </div>
          </div>
        </div>

        {/* CENTER MAP - 55-60% */}
        <div className="flex-1 min-h-0 h-full bg-black bg-opacity-40 rounded border border-gray-700 overflow-hidden relative">
          <div className="map-container absolute inset-0">
            <MapContainer
              whenCreated={(m) => { mapRef.current = m }}
              center={SIKKIM_CENTER}
              zoom={DEFAULT_ZOOM}
              minZoom={MIN_ZOOM}
              maxZoom={MAX_ZOOM}
              maxBounds={SIKKIM_BOUNDS}
              maxBoundsViscosity={1.0}
              zoomControl={true}
              style={{ height: '100%', width: '100%' }}
            >
              {/* Standard OpenStreetMap basemap tiles (key-free, no watermark) */}
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />

              {/* Sikkim State geographic boundary outline (outline only, no mask, full basemap visible) */}
              <Polygon
                positions={SIKKIM_BORDER_RING}
                pathOptions={{
                  fill: false,
                  color: '#0284c7',
                  weight: 2,
                  dashArray: '5, 5',
                  opacity: 0.9,
                }}
                interactive={false}
              />

              {/* Professional GIS Risk Grid Heatmap */}
              {showRisk && sortedCoarse.map((c) => {
                const style = getGridMarkerStyle(c.risk_tier)
                return (
                  <CircleMarker
                    key={c._key}
                    center={[c._lat, c._lon]}
                    radius={style.radius}
                    pathOptions={{
                      fillColor: style.fillColor,
                      fillOpacity: style.fillOpacity,
                      color: style.color,
                      weight: style.weight,
                    }}
                    eventHandlers={{ click: () => openRiskInspector(c) }}
                  >
                    <Popup>
                      <div className="text-sm">
                        <div><strong>Grid:</strong> {c.cell_id ?? c._key}</div>
                        <div><strong>District:</strong> {c.district ?? 'N/A'}</div>
                        <div><strong>Risk Tier:</strong> {c.risk_tier ?? c.risk_category ?? 'N/A'}</div>
                        <div><strong>Risk Score:</strong> {c.risk_score ?? c.risk ?? 'N/A'}</div>
                        <div><strong>Susceptibility (S):</strong> {c.susceptibility_score ?? c.susceptibility ?? 'N/A'}</div>
                      </div>
                    </Popup>
                  </CircleMarker>
                )
              })}

              {/* Hotspots (Rendered above risk grid) */}
              {showHotspots && hotspots.map((s) => (
                <Marker key={s._key} position={[s._lat, s._lon]} icon={hotspotIcon} zIndexOffset={500} eventHandlers={{ click: () => openRiskInspector(s) }}>
                  <Popup>
                    <div className="text-sm">
                      <div><strong>Corridor:</strong> {s.station_name ?? s.corridor_name ?? s.corridor ?? s.location ?? s.station_id ?? 'N/A'}</div>
                      <div><strong>District:</strong> {s.district ?? 'N/A'}</div>
                      <div><strong>Peak Horizon:</strong> {s.forecast_horizon ?? s.peak_horizon ?? 'N/A'}</div>
                      <div><strong>Risk Score:</strong> {s.forecast_risk_score ?? s.risk_score ?? 'N/A'}</div>
                    </div>
                  </Popup>
                </Marker>
              ))}

              {/* Alerts (Rendered above hotspots and risk grid) */}
              {showAlerts && alerts.map((a) => (
                <Marker key={a._key} position={[a._lat, a._lon]} icon={alertIcon} zIndexOffset={1000} eventHandlers={{ click: () => openRiskInspector(a) }}>
                  <Popup>
                    <div className="text-sm">
                      <div><strong>Alert:</strong> {a.alert_id ?? a._key}</div>
                      <div><strong>Location:</strong> {a.location ?? a.place ?? 'N/A'}</div>
                      <div><strong>Severity:</strong> {a.alert_severity ?? a.severity ?? 'N/A'}</div>
                      <div><strong>Horizon:</strong> {a.forecast_horizon ?? 'N/A'}</div>
                      <div><strong>Risk Score:</strong> {a.risk_score ?? 'N/A'}</div>
                      <div><strong>Susceptibility (S):</strong> {a.susceptibility_score ?? a.susceptibility ?? 'N/A'}</div>
                      <div><strong>Rainfall Trigger (R_idx):</strong> {a.r_idx ?? a.rain_idx ?? 'N/A'}</div>
                      <div><strong>Status:</strong> {a.status ?? a.alert_status ?? 'N/A'}</div>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
        </div>

        {/* RIGHT PANEL - 20-25% */}
        <div className="w-1/4 min-h-0 h-full bg-black bg-opacity-60 rounded border border-gray-700 p-3 overflow-y-auto flex flex-col gap-4">
          
          {/* Forecast Horizon Selector */}
          <div>
            <div className="text-sm font-bold mb-2 text-purple-300">📅 Forecast Horizon</div>
            <div className="grid grid-cols-2 gap-1">
              {['+6h', '+12h', '+24h', '+48h'].map(h => (
                <button 
                  key={h}
                  onClick={() => setSelectedHorizon(h)}
                  className={`px-2 py-2 text-xs rounded font-semibold border transition-all ${selectedHorizon === h ? 'bg-blue-600 text-white border-blue-400' : 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700'}`}
                >
                  {h}
                </button>
              ))}
            </div>
          </div>

          {/* Forecast Statistics */}
          <div>
            <div className="text-sm font-bold mb-2 text-yellow-300">📈 Forecast Stats [{selectedHorizon}]</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-gray-800 p-2 rounded border border-gray-700"><div className="text-gray-300">Max Risk</div><div className="font-bold text-white text-lg">{forecastStats.max}</div></div>
              <div className="bg-gray-800 p-2 rounded border border-gray-700"><div className="text-gray-300">Avg Risk</div><div className="font-bold text-white text-lg">{forecastStats.avg}</div></div>
              <div className="bg-gray-800 p-2 rounded border border-gray-700"><div className="text-gray-300">HIGH</div><div className="font-bold text-orange-400 text-lg">{forecastStats.highCount}</div></div>
              <div className="bg-gray-800 p-2 rounded border border-gray-700"><div className="text-gray-300">VERY HIGH</div><div className="font-bold text-red-400 text-lg">{forecastStats.veryHighCount}</div></div>
            </div>
          </div>

          {/* Risk Distribution Chart */}
          <div>
            <div className="text-sm font-bold mb-2 text-green-300">📊 Risk Distribution</div>
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={riskDistribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis dataKey="name" stroke="#999" tick={{fontSize: 11}} />
                <YAxis stroke="#999" tick={{fontSize: 11}} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #666', borderRadius: '4px', color: '#fff', fontSize: '11px' }} />
                <Bar dataKey="count" fill="#10B981" radius={[4, 4, 0, 0]}>
                  {riskDistribution.map((entry, index) => (
                    <Bar key={`bar-${index}`} dataKey="count" fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Alerts Feed */}
          <div>
            <div className="text-sm font-bold mb-2 text-red-300 flex items-center justify-between">
              <span>🚨 Active Alerts</span>
              <span className="text-xs bg-red-600 px-2 py-1 rounded">{filteredAlerts.length}</span>
            </div>
            <div className="mb-2">
              <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="w-full bg-gray-800 text-xs p-1 rounded border border-gray-700">
                <option value="ALL">All Severities</option>
                <option value="HIGH">HIGH only</option>
                <option value="VERY">VERY HIGH only</option>
              </select>
            </div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {loading && alerts.length === 0 ? <div className="text-xs">Loading...</div> : (error && !backendOnline && alerts.length === 0) ? <div className="text-xs text-red-400">{error}</div> : (
                filteredAlerts.length === 0 ? <div className="text-xs text-gray-400">No active alerts</div> : (
                  filteredAlerts.map((a) => (
                    <div key={a._key} className="p-2 bg-gray-800 rounded hover:bg-gray-700 cursor-pointer border border-gray-700 text-xs" onClick={() => centerAndZoom(a._lat, a._lon, 13)}>
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold truncate">{a.alert_id ?? 'Alert'}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${((a.alert_severity||a.severity||'')+'').toUpperCase().includes('VERY') ? 'bg-red-600' : 'bg-orange-500'}`}>{(a.alert_severity || a.severity || 'N/A')}</span>
                      </div>
                      <div className="text-gray-400 truncate">{a.location ?? a.place ?? ''}</div>
                    </div>
                  ))
                )
              )}
            </div>
          </div>

          {/* Top Hotspots */}
          <div>
            <div className="text-sm font-bold mb-2 text-cyan-300">🔥 Top Hotspots</div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {topHotspots.length === 0 ? (
                <div className="text-xs text-gray-400">No hotspots</div>
              ) : (
                topHotspots.map((h, idx) => (
                  <div key={h._key || idx} className="p-2 bg-gray-800 rounded border border-gray-700 text-xs hover:bg-gray-700 cursor-pointer" onClick={() => centerAndZoom(h._lat, h._lon, 12)}>
                    <div className="font-semibold truncate">{h.station_name || h.station_id || 'Hotspot'}</div>
                    <div className="text-gray-400 text-xs">{h.district || 'N/A'}</div>
                    <div className="flex justify-between mt-1 text-xs">
                      <span>Risk: <span className="font-bold text-orange-300">{(h.forecast_risk_score ?? 'N/A').toFixed ? h.forecast_risk_score.toFixed(3) : h.forecast_risk_score}</span></span>
                      <span className="text-gray-400">{h.forecast_horizon || 'N/A'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Risk Inspector Modal - Step 18 (Overlay on top of layout) */}
      {showInspector && selectedRiskLocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40 p-4">
          <div className="inspector-panel w-full max-w-2xl max-h-96 bg-black bg-opacity-80 border border-gray-600 rounded-lg shadow-2xl overflow-y-auto">
            <div className="p-5">
              {/* Header with close button */}
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-700">
                <div className="font-bold text-xl text-cyan-300">🔍 Risk Inspector</div>
                <button onClick={() => setShowInspector(false)} className="text-gray-400 hover:text-white text-2xl font-bold">✕</button>
              </div>

              {/* Risk Details */}
              <div className="bg-gray-800 bg-opacity-60 rounded p-3 mb-3 text-sm border border-gray-700">
                <div className="font-semibold mb-2 text-blue-300">📍 Location Details</div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div><span className="text-gray-400">Location:</span> <span className="font-mono text-white">{(selectedRiskLocation.cell_id ?? selectedRiskLocation.station_name ?? selectedRiskLocation.alert_id ?? selectedRiskLocation._key).substring(0, 20)}</span></div>
                  <div><span className="text-gray-400">Latitude:</span> <span className="text-white">{(() => { const v = Number(selectedRiskLocation._lat ?? selectedRiskLocation.latitude); return isFinite(v) ? v.toFixed(4) : 'N/A' })()}</span></div>
                  <div><span className="text-gray-400">Longitude:</span> <span className="text-white">{(() => { const v = Number(selectedRiskLocation._lon ?? selectedRiskLocation.longitude); return isFinite(v) ? v.toFixed(4) : 'N/A' })()}</span></div>
                  <div><span className="text-gray-400">District:</span> <span className="text-white font-semibold">{selectedRiskLocation.district ?? 'N/A'}</span></div>
                </div>
              </div>

              {/* Risk Profile */}
              <div className="bg-gray-800 bg-opacity-60 rounded p-3 mb-3 text-sm border border-gray-700">
                <div className="font-semibold mb-3 text-yellow-300">📊 Risk Profile</div>
                {(() => {
                  const profile = getRiskProfile()
                  return (
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-gray-700 bg-opacity-70 p-2 rounded border border-gray-600"><div className="text-gray-300">Risk Score</div><div className="font-bold text-white text-lg">{profile.riskScore}</div></div>
                      <div className="bg-gray-700 bg-opacity-70 p-2 rounded border border-gray-600"><div className="text-gray-300">Risk Tier</div><div className="font-bold text-lg" style={{color: riskColor(profile.riskTier)}}>{profile.riskTier}</div></div>
                      <div className="bg-gray-700 bg-opacity-70 p-2 rounded border border-gray-600"><div className="text-gray-300">Susceptibility</div><div className="font-bold text-blue-300 text-lg">{profile.susceptibility}</div></div>
                      <div className="bg-gray-700 bg-opacity-70 p-2 rounded border border-gray-600"><div className="text-gray-300">Rainfall Trigger</div><div className="font-bold text-yellow-300 text-lg">{profile.rainfall}</div></div>
                    </div>
                  )
                })()}
              </div>

              {/* AI Explanation */}
              <div className="bg-gray-800 bg-opacity-60 rounded p-3 mb-3 text-sm border border-gray-700">
                <div className="font-semibold mb-2 text-green-300">🤖 Model-Based Explanation</div>
                <div className="text-xs text-gray-300 mb-2 leading-relaxed">{generateExplanation()}</div>
                <div className="text-xs text-gray-500 italic">⚠️ Statistical associations only; not causal proof.</div>
              </div>

              {/* SHAP Contributing Factors */}
              {shapData && shapData.global_features && shapData.global_features.length > 0 ? (
                <div className="bg-gray-800 bg-opacity-60 rounded p-3 border border-gray-700">
                  <div className="font-semibold mb-3 text-purple-300">📈 Top Contributing Factors</div>
                  <div className="space-y-2">
                    {shapData.global_features.slice(0, 5).map((feat, idx) => {
                      const maxShap = shapData.global_features[0].mean_abs_shap
                      const pct = ((feat.mean_abs_shap / maxShap) * 100).toFixed(0)
                      return (
                        <div key={idx}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-gray-300 font-semibold">{feat.feature}</span>
                            <span className="text-gray-400">{feat.mean_abs_shap.toFixed(3)}</span>
                          </div>
                          <div className="w-full bg-gray-700 rounded h-2.5">
                            <div className="bg-gradient-to-r from-blue-500 to-cyan-400 h-2.5 rounded" style={{width: `${pct}%`}}></div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : (
                <div className="bg-gray-800 bg-opacity-60 rounded p-3 text-xs text-gray-400 border border-gray-700">Detailed local explanation unavailable for this location.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
