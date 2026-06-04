import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { WorldMapData, LLM } from '../types/analytics'
import { LLMBadge, LLM_COLORS } from './LLMBadge'
import { EmptyState } from './LoadingState'

const PROJECTIONS = ['orthographic', 'natural earth', 'mercator', 'azimuthal equal area']
const PROJ_LABELS: Record<string, string> = {
  'orthographic': 'Globe (3D)',
  'natural earth': 'Natural Earth',
  'mercator': 'Mercator',
  'azimuthal equal area': 'Equal Area',
}

interface Props {
  data: WorldMapData
}

export function WorldMap({ data }: Props) {
  const [projection, setProjection] = useState<string>('orthographic')
  const [activeLLMs, setActiveLLMs] = useState<Set<LLM>>(new Set(['Claude', 'Gemini', 'ChatGPT']))

  const toggleLLM = (llm: LLM) => {
    setActiveLLMs(prev => {
      const next = new Set(prev)
      if (next.has(llm)) { if (next.size > 1) next.delete(llm) }
      else next.add(llm)
      return next
    })
  }

  const traces = useMemo(() => {
    return (['Claude', 'Gemini', 'ChatGPT'] as LLM[])
      .filter(llm => activeLLMs.has(llm))
      .map(llm => {
        const d = data[llm]
        const color = LLM_COLORS[llm]
        return {
          type: 'scattergeo' as const,
          lon: d?.lons ?? [],
          lat: d?.lats ?? [],
          mode: 'lines+markers' as const,
          name: llm,
          line: { width: 1.0, color },
          marker: { size: 3, color, opacity: 0.9 },
          hoverinfo: 'text' as const,
          hovertext: d?.texts ?? [],
          opacity: 0.65,
          connectgaps: false,
        }
      })
  }, [data, activeLLMs])

  const hasData = traces.some(t => (t.lat as (number | null)[]).some(v => v !== null))

  if (!hasData) return <EmptyState message="No geo-resolved paths to display. Run the pipeline first." />

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          {(['Claude', 'Gemini', 'ChatGPT'] as LLM[]).map(llm => (
            <button
              key={llm}
              onClick={() => toggleLLM(llm)}
              className={`transition-opacity ${activeLLMs.has(llm) ? 'opacity-100' : 'opacity-30'}`}
            >
              <LLMBadge llm={llm} size="sm" />
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {PROJECTIONS.map(p => (
            <button
              key={p}
              onClick={() => setProjection(p)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                projection === p
                  ? 'bg-white/15 text-white'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              }`}
            >
              {PROJ_LABELS[p]}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl overflow-hidden" style={{ background: 'rgb(10,10,15)' }}>
        <Plot
          data={traces as never}
          layout={{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            margin: { l: 0, r: 0, t: 0, b: 0 },
            showlegend: false,
            geo: {
              projection: { type: projection as never },
              showland: true,
              landcolor: 'rgb(22,22,28)',
              oceancolor: 'rgb(10,10,15)',
              showocean: true,
              showlakes: true,
              lakecolor: 'rgb(10,10,15)',
              showcountries: true,
              countrycolor: 'rgb(55,55,65)',
              showcoastlines: true,
              coastlinecolor: 'rgb(40,40,50)',
              bgcolor: 'rgba(0,0,0,0)',
              resolution: 50,
              framecolor: 'rgba(255,255,255,0.1)',
              framewidth: 1,
            },
            height: 520,
          }}
          config={{ displayModeBar: true, responsive: true, displaylogo: false }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </div>

      <p className="text-xs text-gray-600">
        Each line traces a network path from a RIPE Atlas probe to the LLM endpoint. Private/unresponsive hops are omitted.
        IP geolocation is approximate — backbone IPs resolve to ISP PoP cities, not physical router locations.
      </p>
    </div>
  )
}
