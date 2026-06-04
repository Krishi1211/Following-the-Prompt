export type LLM = 'Claude' | 'Gemini' | 'ChatGPT'

export interface Summary {
  total_traceroutes: number
  unique_ips_resolved: number
  geo_resolved_ips: number
  contributors: string[]
  llm_breakdown: Record<string, number>
  country_breakdown: Record<string, number>
  days_span: number
}

export interface WorldMapTrace {
  lats: (number | null)[]
  lons: (number | null)[]
  texts: (string | null)[]
}

/**
 * Structure: { Claude: { US: { California: trace, Texas: trace, ... }, France: trace, ... } }
 * US paths are nested one level deeper (by state).
 * International paths sit directly under the country key.
 */
export type WorldMapData = Record<
  LLM,
  {
    US?: Record<string, WorldMapTrace>
    [country: string]: WorldMapTrace | Record<string, WorldMapTrace> | undefined
  }
>

export interface CountryExitRow {
  source_country: string
  llm: LLM
  mean_exit_hop: number
  std_exit_hop: number
  count: number
  never_exited_count: number
  top_transit_countries: string[]
}

export interface HopsPerISPRow {
  starting_isp: string
  llm: LLM
  country: string
  mean_hops: number
  std_hops: number
  count: number
  distribution: number[]
}

export interface RTTPerISPRow {
  source_region: string
  starting_isp: string
  llm: LLM
  country: string
  mean_rtt_ms: number
  std_rtt_ms: number
  min_rtt_ms: number
  max_rtt_ms: number
  count: number
}

export interface CommonASRow {
  asn: string
  org_name: string
  llms: string
  llm_count: number
  total_appearances: number
  classification: 'Shared backbone' | 'Partially shared' | 'LLM-specific'
}

export interface HopsToExitASRow {
  source_country: string
  source_isp: string
  llm: LLM
  mean_hops_to_exit: number
  std_hops_to_exit: number
  count: number
  anomaly_count: number
}

export interface AnalyticsData {
  summary: Summary
  worldMap: WorldMapData
  hopsPerISP: HopsPerISPRow[]
  rttPerISP: RTTPerISPRow[]
  commonAS: CommonASRow[]
  hopsToExitAS: HopsToExitASRow[]
  countryExit: CountryExitRow[]
}
