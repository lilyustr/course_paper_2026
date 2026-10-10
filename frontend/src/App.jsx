import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchStations, predictMany } from './api.js'
import Dashboard from './components/Dashboard.jsx'
import StationMap from './components/Map.jsx'

const DEFAULT_TIME = '2026-09-15T08:00'

export default function App() {
  const [stations, setStations] = useState([])
  const [selectedStationId, setSelectedStationId] = useState('')
  const [targetTime, setTargetTime] = useState(DEFAULT_TIME)
  const [predictions, setPredictions] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const selectedStation = useMemo(
    () => stations.find((station) => station.start_station_id === selectedStationId) ?? null,
    [stations, selectedStationId],
  )
  const selectedPrediction = selectedStationId
    ? predictions[selectedStationId] ?? null
    : null

  const runForecast = useCallback(
    async (stationList = stations) => {
      if (!stationList.length) return
      setLoading(true)
      setError('')
      try {
        const ids = stationList.map((station) => station.start_station_id)
        const next = await predictMany(ids, targetTime)
        setPredictions(next)
      } catch (err) {
        setError(
          err?.message ||
            'Could not reach the prediction API. Confirm the FastAPI server is running on port 8000.',
        )
      } finally {
        setLoading(false)
      }
    },
    [stations, targetTime],
  )

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await fetchStations()
        if (cancelled) return
        setStations(data)
        if (data.length) {
          setSelectedStationId(data[0].start_station_id)
        }
      } catch {
        if (!cancelled) {
          setError(
            'Could not load stations from http://127.0.0.1:8000/api/stations. Start the FastAPI backend first.',
          )
        }
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (stations.length) {
      runForecast(stations)
    }
  }, [stations])

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100 text-slate-900">
      <main className="relative h-full min-w-0 flex-1">
        <StationMap
          stations={stations}
          predictions={predictions}
          selectedStationId={selectedStationId}
          onSelectStation={(station) => setSelectedStationId(station.start_station_id)}
        />
        {loading ? (
          <div className="pointer-events-none absolute left-4 top-4 rounded-lg bg-white/90 px-3 py-2 text-sm font-medium text-slate-700 shadow">
            Updating station risk colors…
          </div>
        ) : null}
      </main>
      <Dashboard
        stations={stations}
        selectedStation={selectedStation}
        prediction={selectedPrediction}
        targetTime={targetTime}
        loading={loading}
        error={error}
        onTargetTimeChange={setTargetTime}
        onStationChange={setSelectedStationId}
        onForecast={() => runForecast(stations)}
      />
    </div>
  )
}
