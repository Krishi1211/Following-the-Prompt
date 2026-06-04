import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { RTTPerISPRow, LLM } from '../types/analytics'
import { LLM_COLORS } from './LLMBadge'
import { EmptyState } from './LoadingState'

const LLMs: LLM[] = ['Claude', 'Gemini', 'ChatGPT']

interface Props {
  data: RTTPerISPRow[]
}

export function RTTHeatmap({ data }: Props) {
  const [selectedCountry, setSelectedCountry] = useState<string>('US')
  const [usMode, setUsMode] = useState<'averaged' | 'per_isp'>('averaged')
  const [selectedISP, setSelectedISP] = useState<string>('')

  const countries = useMemo(() => {
    const set = new Set(data.map(r => r.country))
    // Put US first, then sort the rest
    const rest = Array.from(set).filter(c => c !== 'US').sort()
    return ['US', ...rest]
  }, [data])

  // ISPs available for the selected country
  const ispsForCountry = useMemo(() => {
    const set = new Set(data.filter(r => r.country === selectedCountry).map(r => r.starting_isp))
    return Array.from(set).sort()
  }, [data, selectedCountry])

  // When country changes reset ISP selection to first available
  const effectiveISP = selectedISP && ispsForCountry.includes(selectedISP)
    ? selectedISP
    : ispsForCountry[0] ?? ''

  const isUS = selectedCountry === 'US'

  // Regions (x-axis) for the selected country
  const regions = useMemo(() => {
    const set = new Set(
      data
        .filter(r => r.country === selectedCountry)
        .map(r => r.source_region)
    )
    return Array.from(set).sort()
  }, [data, selectedCountry])

  const traces = useMemo(() => {
    return LLMs.map(llm => {
      const byRegion: Record<string, { sum: number; count: number }> = {}

      const rows = data.filter(r => {
        if (r.llm !== llm) return false
        if (r.country !== selectedCountry) return false
        if (isUS && usMode === 'per_isp' && r.starting_isp !== effectiveISP) return false
        return true
      })

      rows.forEach(r => {
        if (!byRegion[r.source_region]) byRegion[r.source_region] = { sum: 0, count: 0 }
        byRegion[r.source_region].sum += r.mean_rtt_ms
        byRegion[r.source_region].count += 1
      })

      const yValues = regions.map(region => {
        const agg = byRegion[region]
        return agg ? Math.round((agg.sum / agg.count) * 10) / 10 : null
      })

      return {
        type: 'bar' as const,
        name: llm,
        x: regions,
        y: yValues,
        marker: { color: LLM_COLORS[llm], opacity: 0.85 },
        hovertemplate: `<b>%{x}</b><br>${llm}: %{y:.1f} ms<extra></extra>`,
      }
    })
  }, [data, selectedCountry, isUS, usMode, effectiveISP, regions])

  if (data.length === 0) return <EmptyState message="No RTT data available" />

  return (
    <div className="flex flex-col gap-4">
      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Country */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Country:</span>
          <select
            value={selectedCountry}
            onChange={e => setSelectedCountry(e.target.value)}
            className="bg-card border border-border text-sm text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-gray-500"
          >
            {countries.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* US-only: ISP mode toggle + ISP picker */}
        {isUS && (
          <>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-1">
              {(['averaged', 'per_isp'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setUsMode(m)}
                  className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                    usMode === m
                      ? 'bg-white/15 text-white'
                      : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                  }`}
                >
                  {m === 'averaged' ? 'ISP Averaged' : 'Per ISP'}
                </button>
              ))}
            </div>

            {usMode === 'per_isp' && (
              <>
                <div className="h-4 w-px bg-border" />
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">ISP:</span>
                  <select
                    value={effectiveISP}
                    onChange={e => setSelectedISP(e.target.value)}
                    className="bg-card border border-border text-sm text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-gray-500 max-w-xs"
                  >
                    {ispsForCountry.map(isp => <option key={isp} value={isp}>{isp}</option>)}
                  </select>
                </div>
              </>
            )}
          </>
        )}
      </div>

      <Plot
        data={traces as never}
        layout={{
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          barmode: 'group',
          xaxis: {
            tickfont: { color: '#9ca3af', size: isUS ? 9 : 11 },
            gridcolor: '#1f1f2a',
            tickangle: isUS ? -45 : -20,
            automargin: true,
          },
          yaxis: {
            title: { text: 'Mean RTT (ms)', font: { color: '#9ca3af', size: 12 } },
            tickfont: { color: '#9ca3af' },
            gridcolor: '#1f1f2a',
            zeroline: false,
          },
          legend: {
            font: { color: '#d1d5db' },
            bgcolor: 'rgba(0,0,0,0)',
            orientation: 'h',
            y: -0.22,
          },
          margin: { l: 60, r: 20, t: 10, b: isUS ? 120 : 80 },
          height: isUS ? 480 : 400,
          hoverlabel: { bgcolor: '#1e1e28', bordercolor: '#3a3a48', font: { color: 'white', size: 12 } },
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />
      <p className="text-xs text-gray-600">
        RTT is taken from the last responding hop in each traceroute (minimum packet RTT to reduce jitter).
        {isUS && usMode === 'averaged' && ' Bars show RTT averaged across all ISPs for each state.'}
        {isUS && usMode === 'per_isp' && ` Bars show RTT for probes originating from ${effectiveISP}.`}
      </p>
    </div>
  )
}
