import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { HopsToExitASRow, LLM } from '../types/analytics'
import { LLM_COLORS } from './LLMBadge'
import { EmptyState } from './LoadingState'

const LLMs: LLM[] = ['Claude', 'Gemini', 'ChatGPT']

interface Props {
  data: HopsToExitASRow[]
}

export function HopsToExitAS({ data }: Props) {
  const [selectedCountry, setSelectedCountry] = useState<string>('All')

  const countries = useMemo(() => {
    const set = new Set(data.map(r => r.source_country))
    return ['All', ...Array.from(set).sort()]
  }, [data])

  const filtered = useMemo(() => {
    if (selectedCountry === 'All') return data
    return data.filter(r => r.source_country === selectedCountry)
  }, [data, selectedCountry])

  // Collect unique ISPs in filtered set
  const isps = useMemo(() => {
    const set = new Set(filtered.map(r => r.source_isp))
    // Sort by average mean hops across LLMs
    const avg: Record<string, number> = {}
    const cnt: Record<string, number> = {}
    filtered.forEach(r => {
      avg[r.source_isp] = (avg[r.source_isp] ?? 0) + r.mean_hops_to_exit
      cnt[r.source_isp] = (cnt[r.source_isp] ?? 0) + 1
    })
    return Array.from(set).sort((a, b) => (avg[b] / cnt[b]) - (avg[a] / cnt[a])).slice(0, 25)
  }, [filtered])

  // Anomaly summary per country
  const anomalyStats = useMemo(() => {
    const byCountry: Record<string, number> = {}
    filtered.forEach(r => {
      byCountry[r.source_country] = (byCountry[r.source_country] ?? 0) + r.anomaly_count
    })
    return byCountry
  }, [filtered])

  if (data.length === 0) return <EmptyState message="No exit-AS data available" />

  const traces = LLMs.map(llm => {
    const byISP: Record<string, HopsToExitASRow> = {}
    filtered.filter(r => r.llm === llm).forEach(r => { byISP[r.source_isp] = r })

    return {
      type: 'bar' as const,
      name: llm,
      x: isps,
      y: isps.map(isp => byISP[isp]?.mean_hops_to_exit ?? null),
      error_y: {
        type: 'data' as const,
        array: isps.map(isp => byISP[isp]?.std_hops_to_exit ?? 0),
        visible: true,
        color: LLM_COLORS[llm] + '60',
      },
      marker: { color: LLM_COLORS[llm], opacity: 0.85 },
      hovertemplate: isps.map(isp => {
        const r = byISP[isp]
        if (!r) return `<b>${isp}</b><br>${llm}: no data<extra></extra>`
        return (
          `<b>${isp}</b><br>${llm}: ${r.mean_hops_to_exit.toFixed(1)} hops<br>` +
          `n=${r.count}` + (r.anomaly_count > 0 ? ` (${r.anomaly_count} never exited)` : '') +
          `<extra></extra>`
        )
      }),
    }
  })

  const totalAnomalies = Object.values(anomalyStats).reduce((a, b) => a + b, 0)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
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
        {totalAnomalies > 0 && (
          <div className="flex items-center gap-2 text-xs text-yellow-500/80 bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-3 py-2">
            ⚠ {totalAnomalies} traceroute{totalAnomalies !== 1 ? 's' : ''} never exited the source AS (excluded from means)
          </div>
        )}
      </div>

      <Plot
        data={traces as never}
        layout={{
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          barmode: 'group',
          xaxis: {
            tickfont: { color: '#9ca3af', size: 10 },
            gridcolor: '#1f1f2a',
            tickangle: -35,
            automargin: true,
          },
          yaxis: {
            title: { text: 'Avg Hops to Exit Source AS', font: { color: '#9ca3af', size: 12 } },
            tickfont: { color: '#9ca3af' },
            gridcolor: '#1f1f2a',
            zeroline: false,
          },
          legend: { font: { color: '#d1d5db' }, bgcolor: 'rgba(0,0,0,0)', orientation: 'h', y: -0.25 },
          margin: { l: 60, r: 20, t: 10, b: 110 },
          height: 420,
          hoverlabel: { bgcolor: '#1e1e28', bordercolor: '#3a3a48', font: { color: 'white', size: 12 } },
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />
      <p className="text-xs text-gray-600">
        Counts consecutive hops from hop 1 with the same ASN as the source IP. The first hop with a different ASN marks the ISP boundary.
        Top 25 ISPs by mean exit hops shown.
      </p>
    </div>
  )
}
