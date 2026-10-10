import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import { riskColor } from '../risk.js'

const JC_CENTER = [40.7178, -74.0431]
const DEFAULT_ZOOM = 14

export default function StationMap({
  stations = [],
  predictions = {},
  selectedStationId,
  onSelectStation,
}) {
  return (
    <MapContainer
      center={JC_CENTER}
      zoom={DEFAULT_ZOOM}
      scrollWheelZoom
      className="h-full w-full"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {stations.map((station) => {
        const prediction = predictions[station.start_station_id]
        const color = riskColor(prediction?.operational_risk)
        const selected = station.start_station_id === selectedStationId

        return (
          <CircleMarker
            key={station.start_station_id}
            center={[station.start_lat, station.start_lng]}
            radius={selected ? 12 : 8}
            pathOptions={{
              color: selected ? '#0f172a' : color,
              weight: selected ? 3 : 1.5,
              fillColor: color,
              fillOpacity: 0.9,
            }}
            eventHandlers={{
              click: () => onSelectStation(station),
            }}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              <div className="text-xs">
                <strong>{station.start_station_name}</strong>
                <div>{station.start_station_id}</div>
                {prediction ? (
                  <div>
                    {prediction.predicted_trip_count} trips · {prediction.operational_risk}
                  </div>
                ) : (
                  <div>Click to forecast</div>
                )}
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
