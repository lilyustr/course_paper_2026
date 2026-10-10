import axios from 'axios'

export const API_BASE = 'http://127.0.0.1:8000'

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

export async function fetchStations() {
  const { data } = await client.get('/api/stations')
  return data
}

export async function predictDemand(stationId, targetTime) {
  const payload = { station_id: stationId }
  if (targetTime) {
    payload.target_time = targetTime.length === 16 ? `${targetTime}:00` : targetTime
  }
  const { data } = await client.post('/api/predict', payload)
  return data
}

export async function predictMany(stationIds, targetTime, concurrency = 8) {
  const results = {}
  let index = 0

  async function worker() {
    while (index < stationIds.length) {
      const current = index
      index += 1
      const stationId = stationIds[current]
      try {
        results[stationId] = await predictDemand(stationId, targetTime)
      } catch {
        results[stationId] = null
      }
    }
  }

  const workers = Array.from(
    { length: Math.min(concurrency, stationIds.length) },
    () => worker(),
  )
  await Promise.all(workers)
  return results
}
