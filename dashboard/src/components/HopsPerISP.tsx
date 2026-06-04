import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { HopsPerISPRow } from '../types/analytics'
import { LLM_COLORS } from './LLMBadge'
import { EmptyState } from './LoadingState'

const LLMs = ['Claude', 'Gemini', 'ChatGPT'] as const

interface Props {
  data: HopsPerISPRow[]
}

export function HopsPerISP({ data }: Props) {
  const [chartType, setChartType] = useState<'bar' | 'box'>('bar')
  const [countryFilter, setCountryFilter] = useState<string>('All')

  const countries = useMemo(() => {
    const set = new Set(data.map(r => r.country))
    return ['All', ...Array.from(set).sort()]
  }, [data])

  const filtered = useMemo(() => {
    if (countryFilter === 'All') return data
    return data.filter(r => r.country === countryFilter)
  }, [data, countryFilter])

  // Sort ISPs by average mean hops descending
  const sortedISPs = useMemo(() => {
    const totals: Record<string, number> = {}
    const counts: Record<string, number> = {}
    filtered.forEach(r => {
      totals[r.starting_isp] = (totals[r.starting_isp] ?? 0) + r.mean_hops
      counts[r.starting_isp] = (counts[r.starting_isp] ?? 0) + 1
    })
    return Object.keys(totals)
      .sort((a, b) => totals[b] / counts[b] - totals[a] / counts[a])
      .slice(0, 30)
  }, [filtered])

  if (data.length === 0) return <EmptyState message="No hop data available" />

  const traces = LLMs.map(llm => {
    const byISP: Record<string, HopsPerISPRow> = {}
    filtered.filter(r => r.llm === llm).forEach(r => { byISP[r.starting_isp] = r })

    if (chartType === 'bar') {
      return {
        type: 'bar' as const,
        name: llm,
        x: sortedISPs,
        y: sortedISPs.map(isp => byISP[isp]?.mean_hops ?? null),
        error_y: {
          type: 'data' as const,
          array: sortedISPs.map(isp => byISP[isp]?.std_hops ?? 0),
          visible: true,
          color: LLM_COLORS[llm] + '60',
        },
        marker: { color: LLM_COLORS[llm], opacity: 0.85 },
        hovertemplate: `<b>%{x}</b><br>${llm}: %{y:.1f} hops ± %{error_y.array:.1f}<extra></extra>`,
      }
    } else {
      const allRows = filtered.filter(r => r.llm === llm)
      const grouped: Record<string, number[]> = {}
      allRows.forEach(r => {
        if (!grouped[r.starting_isp]) grouped[r.starting_isp] = []
        grouped[r.starting_isp].push(...r.distribution)
      })
      return {
        type: 'box' as const,
        name: llm,
        x: sortedISPs.flatMap(isp => (grouped[isp] ?? []).map(() => isp)),
        y: sortedISPs.flatMap(isp => grouped[isp] ?? []),
        marker: { color: LLM_COLORS[llm] },
        boxmean: 'sd' as const,
        hovertemplate: `<b>%{x}</b><br>${llm}: %{y} hops<extra></extra>`,
      }
    }
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">View:</span>
          {(['bar', 'box'] as const).map(t => (
            <button
              key={t}
              onClick={() => setChartType(t)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                chartType === t ? 'bg-white/15 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              }`}
            >
              {t === 'bar' ? 'Grouped Bar' : 'Box Plot'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Region:</span>
          <select
            value={countryFilter}
            onChange={e => setCountryFilter(e.target.value)}
            className="bg-card border border-border text-sm text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-gray-500"
          >
            {countries.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      <Plot
        data={traces as never}
        layout={{
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          barmode: chartType === 'bar' ? 'group' : undefined,
          xaxis: {
            tickfont: { color: '#9ca3af', size: 10 },
            gridcolor: '#1f1f2a',
            tickangle: -35,
            automargin: true,
          },
          yaxis: {
            title: { text: 'Hop Count', font: { color: '#9ca3af', size: 12 } },
            tickfont: { color: '#9ca3af' },
            gridcolor: '#1f1f2a',
            zeroline: false,
          },
          legend: { font: { color: '#d1d5db' }, bgcolor: 'rgba(0,0,0,0)', orientation: 'h', y: -0.25 },
          margin: { l: 50, r: 20, t: 20, b: 100 },
          height: 420,
          hoverlabel: { bgcolor: '#1e1e28', bordercolor: '#3a3a48', font: { color: 'white', size: 12 } },
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />
      <p className="text-xs text-gray-600">
        Starting ISP is identified from the first non-private hop in each traceroute. Top 30 ISPs by average hop count shown.
      </p>
    </div>
  )
}
