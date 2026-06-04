import { useState, useEffect } from 'react'
import type { AnalyticsData, Summary, WorldMapData, HopsPerISPRow, RTTPerISPRow, CommonASRow, HopsToExitASRow } from '../types/analytics'

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  return res.json() as Promise<T>
}

export function useAnalyticsData() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [summary, worldMap, hopsPerISP, rttPerISP, commonAS, hopsToExitAS] =
          await Promise.all([
            fetchJSON<Summary>('/data/summary.json'),
            fetchJSON<WorldMapData>('/data/world_map.json'),
            fetchJSON<HopsPerISPRow[]>('/data/hops_per_isp.json'),
            fetchJSON<RTTPerISPRow[]>('/data/rtt_per_isp.json'),
            fetchJSON<CommonASRow[]>('/data/common_as.json'),
            fetchJSON<HopsToExitASRow[]>('/data/hops_to_exit_as.json'),
          ])
        setData({ summary, worldMap, hopsPerISP, rttPerISP, commonAS, hopsToExitAS })
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Unknown error loading data')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return { data, loading, error }
}
