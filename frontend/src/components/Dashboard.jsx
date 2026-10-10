import {
  AlertTriangle,
  Bike,
  Clock3,
  MapPin,
  Navigation,
  RefreshCw,
} from 'lucide-react'
import { riskColor } from '../risk.js'

function statusBadge(prediction) {
  if (!prediction) {
    return { label: 'Awaiting forecast', className: 'bg-slate-100 text-slate-600' }
  }
  const risk = prediction.operational_risk
  if (risk === 'SHORTAGE_RISK') {
    return { label: 'Shortage risk', className: 'bg-red-100 text-red-700' }
  }
  if (risk === 'OVERFLOW_RISK') {
    return { label: 'Overflow risk', className: 'bg-amber-100 text-amber-800' }
  }
  return { label: 'Normal', className: 'bg-emerald-100 text-emerald-700' }
}

export default function Dashboard({
  stations,
  selectedStation,
  prediction,
  targetTime,
  loading,
  error,
  onTargetTimeChange,
  onStationChange,
  onForecast,
}) {
  const badge = statusBadge(prediction)
  const accent = riskColor(prediction?.operational_risk)

  return (
    <aside className="flex h-full w-full max-w-md flex-col border-l border-slate-200 bg-white/95 shadow-xl backdrop-blur">
      <header className="border-b border-slate-100 px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
          Decision support
        </p>
        <h1 className="mt-1 text-xl font-semibold text-slate-900">
          Citi Bike demand forecast
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Jersey City hourly trip demand and rebalancing guidance.
        </p>
      </header>

      <form
        className="space-y-3 border-b border-slate-100 px-5 py-4"
        onSubmit={(event) => {
          event.preventDefault()
          onForecast()
        }}
      >
        <label className="block text-sm font-medium text-slate-700">
          Station
          <select
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-sky-500 focus:ring-2"
            value={selectedStation?.start_station_id ?? ''}
            onChange={(event) => onStationChange(event.target.value)}
          >
            <option value="" disabled>
              Select a station
            </option>
            {stations.map((station) => (
              <option key={station.start_station_id} value={station.start_station_id}>
                {station.start_station_name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Forecast date and time
          <input
            type="datetime-local"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-sky-500 focus:ring-2"
            value={targetTime}
            onChange={(event) => onTargetTimeChange(event.target.value)}
          />
        </label>

        <button
          type="submit"
          disabled={loading || !selectedStation}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sky-700 px-3 py-2.5 text-sm font-semibold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Forecasting stations…' : 'Run forecast'}
        </button>
      </form>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {error ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        {!selectedStation ? (
          <p className="text-sm text-slate-500">
            Choose a station on the map or from the list to see the forecast.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 p-4">
              <div className="flex items-start gap-3">
                <span
                  className="mt-0.5 h-3 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: accent }}
                />
                <div>
                  <h2 className="font-semibold text-slate-900">
                    {selectedStation.start_station_name}
                  </h2>
                  <p className="text-xs text-slate-500">{selectedStation.start_station_id}</p>
                </div>
              </div>

              <dl className="mt-4 grid grid-cols-1 gap-3 text-sm">
                <div className="flex items-center gap-2 text-slate-600">
                  <MapPin className="h-4 w-4 text-slate-400" />
                  {selectedStation.start_lat.toFixed(5)}, {selectedStation.start_lng.toFixed(5)}
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <Clock3 className="h-4 w-4 text-slate-400" />
                  {prediction?.forecast_hour
                    ? new Date(prediction.forecast_hour).toLocaleString()
                    : 'No forecast hour yet'}
                </div>
              </dl>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="flex items-center gap-1 text-xs uppercase tracking-wide text-slate-500">
                  <Bike className="h-3.5 w-3.5" /> Predicted trips
                </p>
                <p className="mt-1 text-2xl font-semibold text-slate-900">
                  {prediction ? prediction.predicted_trip_count.toFixed(1) : '—'}
                </p>
                <p className="text-xs text-slate-500">
                  Lag 1h: {prediction ? prediction.lag_1h : '—'}
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="flex items-center gap-1 text-xs uppercase tracking-wide text-slate-500">
                  <AlertTriangle className="h-3.5 w-3.5" /> Risk status
                </p>
                <p className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${badge.className}`}>
                  {prediction?.risk_status ?? badge.label}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  {prediction?.operational_risk ?? 'Select a time and run forecast'}
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-sky-100 bg-sky-50 p-4">
              <p className="flex items-center gap-2 text-sm font-semibold text-sky-900">
                <Navigation className="h-4 w-4" />
                Rebalancing action
              </p>
              <p className="mt-2 text-sm leading-6 text-sky-950">
                {prediction?.rebalancing_suggestion ??
                  'Run a forecast to get a station-specific rebalancing suggestion.'}
              </p>
            </div>
          </div>
        )}
      </div>

      <footer className="space-y-2 border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-red-600" /> Shortage
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> Overflow
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" /> Normal
          </span>
        </div>
      </footer>
    </aside>
  )
}
