import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { WorldMapData, WorldMapTrace, LLM } from '../types/analytics'
import { LLMBadge, LLM_COLORS } from './LLMBadge'
import { EmptyState } from './LoadingState'

const LLMs: LLM[] = ['Claude', 'Gemini', 'ChatGPT']

const PROJECTIONS: { value: string; label: string }[] = [
  { value: 'natural earth',        label: 'Flat' },
  { value: 'orthographic',         label: 'Globe' },
  { value: 'mercator',             label: 'Mercator' },
  { value: 'azimuthal equal area', label: 'Equal Area' },
]

function getTrace(data: WorldMapData, llm: LLM, country: string, state: string): WorldMapTrace | null {
  const llmData = data[llm]
  if (!llmData) return null
  if (country === 'US') {
    const usData = llmData['US'] as Record<string, WorldMapTrace> | undefined
    return usData?.[state] ?? null
  }
  return (llmData[country] as WorldMapTrace | undefined) ?? null
}

interface Props {
  data: WorldMapData
}

export function WorldMap({ data }: Props) {
  // Derive available countries from the Claude entry (all LLMs share same geography)
  const countries = useMemo(() => {
    const claudeData = data['Claude'] ?? {}
    const keys = Object.keys(claudeData)
    // Put US first
    return ['US', ...keys.filter(k => k !== 'US')].sort((a, b) =>
      a === 'US' ? -1 : b === 'US' ? 1 : a.localeCompare(b)
    )
  }, [data])

  const [selectedCountry, setSelectedCountry] = useState<string>('US')
  const [selectedState, setSelectedState]     = useState<string>('California')
  const [activeLLMs, setActiveLLMs]           = useState<Set<LLM>>(new Set(LLMs))
  const [projection, setProjection]           = useState<string>('natural earth')

  const states = useMemo(() => {
    const usData = (data['Claude']?.['US'] ?? {}) as Record<string, WorldMapTrace>
    return Object.keys(usData).sort()
  }, [data])

  // When switching away from US, reset to first available country
  const handleCountryChange = (c: string) => {
    setSelectedCountry(c)
    if (c === 'US' && !states.includes(selectedState)) {
      setSelectedState(states[0] ?? '')
    }
  }

  const toggleLLM = (llm: LLM) => {
    setActiveLLMs(prev => {
      const next = new Set(prev)
      if (next.has(llm) && next.size > 1) next.delete(llm)
      else next.add(llm)
      return next
    })
  }

  const traces = useMemo(() => {
    return LLMs.filter(llm => activeLLMs.has(llm)).flatMap(llm => {
      const trace = getTrace(data, llm, selectedCountry, selectedState)
      if (!trace || trace.lats.length === 0) return []

      const color = LLM_COLORS[llm]
      return [{
        type: 'scattergeo' as const,
        name: llm,
        lon: trace.lons,
        lat: trace.lats,
        mode: 'lines+markers' as const,
        line:   { width: 0.9, color },
        marker: { size: 2.5, color, opacity: 1 },
        hoverinfo: 'text' as const,
        hovertext: trace.texts,
        opacity: 0.75,
        connectgaps: false,
      }]
    })
  }, [data, selectedCountry, selectedState, activeLLMs])

  const hasData = traces.some(t => (t.lat as (number | null)[]).some(v => v !== null))

  // Geo scope: zoom into US when showing US states
  const geoScope = selectedCountry === 'US' ? 'usa' : 'world'
  const geoProjection = selectedCountry === 'US' ? 'albers usa' : projection

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Country selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Country:</span>
          <select
            value={selectedCountry}
            onChange={e => handleCountryChange(e.target.value)}
            className="bg-card border border-border text-sm text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-gray-500"
          >
            {countries.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* State selector — only for US */}
        {selectedCountry === 'US' && (
          <>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">State:</span>
              <select
                value={selectedState}
                onChange={e => setSelectedState(e.target.value)}
                className="bg-card border border-border text-sm text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-gray-500"
              >
                {states.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </>
        )}

        <div className="h-4 w-px bg-border" />

        {/* LLM toggles */}
        <div className="flex gap-1.5">
          {LLMs.map(llm => (
            <button
              key={llm}
              onClick={() => toggleLLM(llm)}
              className={`transition-opacity duration-150 ${activeLLMs.has(llm) ? 'opacity-100' : 'opacity-25'}`}
            >
              <LLMBadge llm={llm} size="sm" />
            </button>
          ))}
        </div>

        {/* Projection — only for non-US (US always uses Albers) */}
        {selectedCountry !== 'US' && (
          <>
            <div className="h-4 w-px bg-border ml-auto" />
            <div className="flex gap-1">
              {PROJECTIONS.map(p => (
                <button
                  key={p.value}
                  onClick={() => setProjection(p.value)}
                  className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
                    projection === p.value
                      ? 'bg-white/15 text-white'
                      : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Map */}
      {!hasData ? (
        <EmptyState message={`No resolved paths for ${selectedCountry === 'US' ? selectedState : selectedCountry}. Run the pipeline first.`} />
      ) : (
        <div className="rounded-xl overflow-hidden" style={{ background: 'rgb(10,10,15)' }}>
          <Plot
            data={traces as never}
            layout={{
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor:  'rgba(0,0,0,0)',
              margin: { l: 0, r: 0, t: 0, b: 0 },
              showlegend: false,
              height: 500,
              geo: {
                scope: geoScope as never,
                projection: { type: geoProjection as never },
                showland: true,
                landcolor:      selectedCountry === 'US' ? 'rgb(28,28,36)' : 'rgb(22,22,28)',
                oceancolor:     'rgb(10,10,15)',
                showocean:      true,
                showlakes:      true,
                lakecolor:      'rgb(10,10,15)',
                showcountries:  true,
                countrycolor:   'rgb(55,55,68)',
                showcoastlines: true,
                coastlinecolor: 'rgb(44,44,56)',
                showsubunits:   true,
                subunitcolor:   'rgb(44,44,56)',
                bgcolor:        'rgba(0,0,0,0)',
                framecolor:     'rgba(255,255,255,0.08)',
                framewidth:     1,
                resolution:     50,
              },
            }}
            config={{
              displayModeBar:  true,
              displaylogo:     false,
              modeBarButtonsToRemove: ['select2d', 'lasso2d', 'toImage'],
              responsive: true,
            }}
            style={{ width: '100%' }}
            useResizeHandler
          />
        </div>
      )}

      <p className="text-xs text-gray-600">
        {selectedCountry === 'US'
          ? `Showing traceroutes from RIPE Atlas probes in ${selectedState}. Switch state to compare routing behaviour across the US.`
          : `Showing traceroutes from probes in ${selectedCountry}. Private and unresponsive hops are omitted. Positions are ISP PoP estimates, not physical router locations.`}
      </p>
    </div>
  )
}
