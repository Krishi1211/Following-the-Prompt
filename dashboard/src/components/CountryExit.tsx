import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { CountryExitRow, LLM } from '../types/analytics'
import { LLM_COLORS } from './LLMBadge'
import { EmptyState } from './LoadingState'

const LLMs: LLM[] = ['Claude', 'Gemini', 'ChatGPT']

const COUNTRY_ORDER = ['France', 'India', 'Kenya', 'Pakistan', 'South Africa', 'UK', 'US']

interface Props {
  data: CountryExitRow[]
}

export function CountryExit({ data }: Props) {
  const [selectedCountry, setSelectedCountry] = useState<string>('All')

  const countries = useMemo(() => {
    const set = new Set(data.map(r => r.source_country))
    return ['All', ...COUNTRY_ORDER.filter(c => set.has(c)), ...Array.from(set).filter(c => !COUNTRY_ORDER.includes(c)).sort()]
  }, [data])

  const filtered = useMemo(() =>
    selectedCountry === 'All' ? data : data.filter(r => r.source_country === selectedCountry),
    [data, selectedCountry]
  )

  // X-axis: countries in a stable order
  const xCountries = useMemo(() => {
    const set = new Set(filtered.map(r => r.source_country))
    return COUNTRY_ORDER.filter(c => set.has(c))
  }, [filtered])

  // Detail panel: transit countries for selected source country per LLM
  const transitDetail = useMemo(() => {
    if (selectedCountry === 'All') return null
    const byLLM: Record<string, string[]> = {}
    filtered.forEach(r => { byLLM[r.llm] = r.top_transit_countries })
    return byLLM
  }, [filtered, selectedCountry])

  const barTraces = useMemo(() => LLMs.map(llm => {
    const byCountry: Record<string, CountryExitRow> = {}
    filtered.filter(r => r.llm === llm).forEach(r => { byCountry[r.source_country] = r })

    return {
      type: 'bar' as const,
      name: llm,
      x: xCountries,
      y: xCountries.map(c => byCountry[c]?.mean_exit_hop ?? null),
      error_y: {
        type: 'data' as const,
        array: xCountries.map(c => byCountry[c]?.std_exit_hop ?? 0),
        visible: true,
        color: LLM_COLORS[llm] + '55',
      },
      marker: { color: LLM_COLORS[llm], opacity: 0.85 },
      hovertemplate: xCountries.map(c => {
        const r = byCountry[c]
        if (!r) return `<b>%{x}</b><br>${llm}: no data<extra></extra>`
        const anomaly = r.never_exited_count > 0 ? `<br>Never exited: ${r.never_exited_count}` : ''
        return (
          `<b>%{x}</b><br>` +
          `${llm}: %{y:.1f} hops ± ${r.std_exit_hop.toFixed(1)}<br>` +
          `Traceroutes: ${r.count}${anomaly}<extra></extra>`
        )
      }),
    }
  }), [filtered, xCountries])

  if (data.length === 0) return <EmptyState message="No country exit data available" />

  return (
    <div className="flex flex-col gap-5">
      {/* Controls */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500">Source country:</span>
        <div className="flex flex-wrap gap-1">
          {countries.map(c => (
            <button
              key={c}
              onClick={() => setSelectedCountry(c)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                selectedCountry === c
                  ? 'bg-white/15 text-white'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Bar chart */}
      <Plot
        data={barTraces as never}
        layout={{
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor:  'rgba(0,0,0,0)',
          barmode: 'group',
          xaxis: {
            tickfont:    { color: '#9ca3af', size: 11 },
            gridcolor:   '#1f1f2a',
            automargin:  true,
          },
          yaxis: {
            title:     { text: 'Avg hop # of first country exit', font: { color: '#9ca3af', size: 12 } },
            tickfont:  { color: '#9ca3af' },
            gridcolor: '#1f1f2a',
            zeroline:  false,
          },
          legend: { font: { color: '#d1d5db' }, bgcolor: 'rgba(0,0,0,0)', orientation: 'h', y: -0.2 },
          margin: { l: 60, r: 20, t: 10, b: 60 },
          height: 380,
          hoverlabel: { bgcolor: '#1e1e28', bordercolor: '#3a3a48', font: { color: 'white', size: 12 } },
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />

      {/* Transit country detail — only when a single country is selected */}
      {transitDetail && (
        <div className="glass-card p-4 space-y-3">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">
            Countries transited en route from {selectedCountry}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {LLMs.map(llm => {
              const transit = transitDetail[llm] ?? []
              return (
                <div key={llm} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ background: LLM_COLORS[llm] }}
                    />
                    <span className="text-sm font-medium text-gray-300">{llm}</span>
                  </div>
                  {transit.length === 0 ? (
                    <p className="text-xs text-gray-600 pl-4">No transit data</p>
                  ) : (
                    <div className="flex flex-wrap gap-1 pl-4">
                      {transit.map((country, i) => (
                        <span key={country} className="flex items-center gap-1 text-xs text-gray-400">
                          {i > 0 && <span className="text-gray-700">→</span>}
                          <span
                            className="px-2 py-0.5 rounded bg-white/5 border border-white/10"
                          >
                            {country}
                          </span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      <p className="text-xs text-gray-600">
        A country exit is detected when a traceroute hop resolves to a country different from the probe's source country.
        The Y-axis shows the average hop number at which this first occurs. Lower = traffic leaves sooner.
        "Never exited" traceroutes (all hops remain in-country or unresolved) are excluded from the mean but counted separately.
      </p>
    </div>
  )
}
