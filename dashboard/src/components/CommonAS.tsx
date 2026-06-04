import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { CommonASRow } from '../types/analytics'
import { EmptyState } from './LoadingState'

const CLASS_COLORS: Record<string, string> = {
  'Shared backbone':  '#8B5CF6',  // purple — appears in all 3
  'Partially shared': '#F59E0B',  // amber — appears in 2
  'LLM-specific':     '#6B7280',  // gray — appears in 1
}

// Map "Claude, Gemini" etc to more specific colors
const LLM_SET_COLORS: Record<string, string> = {
  'Claude, Gemini, ChatGPT': '#8B5CF6',
  'Gemini, ChatGPT':         '#3B82F6',
  'Claude, ChatGPT':         '#F97316',
  'Claude, Gemini':          '#EC4899',
  'ChatGPT':                 '#16A34A',
  'Gemini':                  '#2563EB',
  'Claude':                  '#D97706',
}

interface Props {
  data: CommonASRow[]
}

export function CommonAS({ data }: Props) {
  const [sortBy, setSortBy] = useState<'appearances' | 'commonality'>('appearances')
  const [filterClass, setFilterClass] = useState<string>('All')

  const filtered = useMemo(() => {
    if (filterClass === 'All') return data
    return data.filter(r => r.classification === filterClass)
  }, [data, filterClass])

  const sorted = useMemo(() => {
    const arr = [...filtered]
    if (sortBy === 'commonality') {
      arr.sort((a, b) => b.llm_count - a.llm_count || b.total_appearances - a.total_appearances)
    } else {
      arr.sort((a, b) => b.total_appearances - a.total_appearances)
    }
    return arr.slice(0, 30)
  }, [filtered, sortBy])

  if (data.length === 0) return <EmptyState message="No AS data available" />

  const labels = sorted.map(r => `AS${r.asn.replace('AS', '')} — ${r.org_name.slice(0, 28)}`)
  const colors = sorted.map(r => LLM_SET_COLORS[r.llms] ?? CLASS_COLORS[r.classification] ?? '#6B7280')
  const outlineWidths = sorted.map(r => r.classification === 'Shared backbone' ? 2 : 0)
  const outlineColors = sorted.map(r => r.classification === 'Shared backbone' ? '#ffffff80' : 'transparent')

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Sort by:</span>
          {(['appearances', 'commonality'] as const).map(s => (
            <button
              key={s}
              onClick={() => setSortBy(s)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                sortBy === s ? 'bg-white/15 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              }`}
            >
              {s === 'appearances' ? 'Total Appearances' : 'Commonality (all-3 first)'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Filter:</span>
          {['All', 'Shared backbone', 'Partially shared', 'LLM-specific'].map(c => (
            <button
              key={c}
              onClick={() => setFilterClass(c)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                filterClass === c ? 'bg-white/15 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(LLM_SET_COLORS).map(([llmSet, color]) => (
          <div key={llmSet} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ background: color }} />
            <span className="text-xs text-gray-400">{llmSet}</span>
          </div>
        ))}
      </div>

      <Plot
        data={[{
          type: 'bar' as const,
          orientation: 'h' as const,
          x: sorted.map(r => r.total_appearances),
          y: labels,
          marker: {
            color: colors,
            line: { color: outlineColors, width: outlineWidths },
          },
          hovertemplate: sorted.map(r =>
            `<b>AS${r.asn} — ${r.org_name}</b><br>` +
            `Appears in: ${r.llms}<br>` +
            `Classification: ${r.classification}<br>` +
            `Total hop records: ${r.total_appearances}<extra></extra>`
          ),
          text: sorted.map(r => r.classification === 'Shared backbone' ? '★' : ''),
          textposition: 'outside' as const,
          textfont: { color: '#ffffff', size: 14 },
        }] as never}
        layout={{
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          xaxis: {
            title: { text: 'Total Hop Record Appearances', font: { color: '#9ca3af', size: 12 } },
            tickfont: { color: '#9ca3af' },
            gridcolor: '#1f1f2a',
          },
          yaxis: {
            tickfont: { color: '#e5e7eb', size: 10 },
            automargin: true,
          },
          margin: { l: 260, r: 40, t: 10, b: 50 },
          height: Math.max(360, sorted.length * 22 + 60),
          hoverlabel: { bgcolor: '#1e1e28', bordercolor: '#3a3a48', font: { color: 'white', size: 12 } },
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />
      <p className="text-xs text-gray-600">
        ★ = Shared backbone (appears in all 3 LLM traceroutes). Colors indicate which LLMs share each autonomous system.
        Top 30 ASes shown.
      </p>
    </div>
  )
}
