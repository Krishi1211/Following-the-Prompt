import { useState } from 'react'
import { useAnalyticsData } from './hooks/useAnalyticsData'
import { StatCard } from './components/StatCard'
import { LLMBadge } from './components/LLMBadge'
import { WorldMap } from './components/WorldMap'
import { HopsPerISP } from './components/HopsPerISP'
import { RTTHeatmap } from './components/RTTHeatmap'
import { CommonAS } from './components/CommonAS'
import { HopsToExitAS } from './components/HopsToExitAS'
import { CountryExit } from './components/CountryExit'
import { LoadingState, ErrorState } from './components/LoadingState'

type Tab = 'map' | 'hops' | 'rtt' | 'as' | 'exit' | 'border'

const TABS: { id: Tab; label: string; icon: string; desc: string }[] = [
  { id: 'map',    label: 'Route Map',         icon: '🌐', desc: 'Traceroute paths by country / state' },
  { id: 'hops',   label: 'Hops per ISP',      icon: '📊', desc: 'Hop count by starting ISP per LLM' },
  { id: 'rtt',    label: 'Latency / RTT',     icon: '⚡', desc: 'End-to-end RTT by ISP and region' },
  { id: 'as',     label: 'Shared Backbone',   icon: '🔗', desc: 'Autonomous systems shared across LLMs' },
  { id: 'exit',   label: 'ISP Boundary',      icon: '🚪', desc: 'Hops to leave source ISP\'s network' },
  { id: 'border', label: 'Country Boundary',  icon: '🗺️', desc: 'When and where traffic crosses country borders' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('map')
  const { data, loading, error } = useAnalyticsData()

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#0a0a0f' }}>
      {/* Header */}
      <header className="header-gradient px-6 py-4 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 flex items-center justify-center">
              <div className="absolute inset-0 rounded-lg" style={{ background: 'linear-gradient(135deg, #D97706, #2563EB, #16A34A)', opacity: 0.8 }} />
              <span className="relative text-white font-bold text-sm z-10">RA</span>
            </div>
            <div>
              <h1 className="text-white font-semibold text-base leading-none">RIPE Atlas</h1>
              <p className="text-gray-500 text-xs mt-0.5">LLM Routing Analytics</p>
            </div>
          </div>
          <div className="h-6 w-px bg-border hidden sm:block" />
          <div className="hidden sm:flex items-center gap-2">
            {(['Claude', 'Gemini', 'ChatGPT'] as const).map(llm => (
              <LLMBadge key={llm} llm={llm} size="sm" />
            ))}
          </div>
        </div>

        {data && (
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span><span className="text-gray-300 font-medium">{data.summary.total_traceroutes.toLocaleString()}</span> traceroutes</span>
            <span><span className="text-gray-300 font-medium">{data.summary.contributors.join(', ')}</span></span>
            <span className="hidden md:inline"><span className="text-gray-300 font-medium">{data.summary.days_span}</span> days</span>
          </div>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <nav className="w-56 flex-shrink-0 border-r border-border bg-card flex flex-col py-4 px-3 gap-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`nav-item text-left ${activeTab === tab.id ? 'active' : ''}`}
            >
              <span className="text-base">{tab.icon}</span>
              <span className="leading-tight">
                <span className="block">{tab.label}</span>
                <span className="text-xs text-gray-600 font-normal hidden xl:block">{tab.desc}</span>
              </span>
            </button>
          ))}

          {/* Data info at bottom */}
          <div className="mt-auto pt-4 border-t border-border">
            {data ? (
              <div className="px-2 space-y-2">
                <p className="text-xs text-gray-600 font-medium uppercase tracking-wide">Coverage</p>
                {Object.entries(data.summary.llm_breakdown).map(([llm, count]) => (
                  <div key={llm} className="flex items-center justify-between">
                    <LLMBadge llm={llm as never} size="sm" />
                    <span className="text-xs text-gray-500">{count}</span>
                  </div>
                ))}
                <div className="pt-1 space-y-1">
                  {Object.entries(data.summary.country_breakdown).slice(0, 5).map(([country, count]) => (
                    <div key={country} className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">{country}</span>
                      <span className="text-xs text-gray-600">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-gray-700 px-2">No data loaded</p>
            )}
          </div>
        </nav>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">
          {loading && <LoadingState />}
          {error && <ErrorState message={error} />}
          {data && (
            <div className="max-w-7xl mx-auto space-y-6">
              {/* Summary stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  label="Total Traceroutes"
                  value={data.summary.total_traceroutes}
                  sub={`across ${data.summary.contributors.length} contributors`}
                  accentColor="#8B5CF6"
                />
                <StatCard
                  label="Unique IPs Resolved"
                  value={data.summary.unique_ips_resolved}
                  sub={`${data.summary.geo_resolved_ips.toLocaleString()} geo-located`}
                  accentColor="#06B6D4"
                />
                <StatCard
                  label="Days of Data"
                  value={data.summary.days_span}
                  sub={`${data.summary.contributors.join(' · ')}`}
                  accentColor="#F59E0B"
                />
                <StatCard
                  label="Regions Covered"
                  value={Object.keys(data.summary.country_breakdown).length}
                  sub={`US states + ${Object.keys(data.summary.country_breakdown).filter(c => c !== 'US').length} countries`}
                  accentColor="#10B981"
                />
              </div>

              {/* Active chart */}
              <div className="chart-container">
                <div className="mb-5 pb-4 border-b border-border">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{TABS.find(t => t.id === activeTab)?.icon}</span>
                    <div>
                      <h2 className="text-white font-semibold text-lg">
                        {TABS.find(t => t.id === activeTab)?.label}
                      </h2>
                      <p className="text-gray-500 text-sm">
                        {TABS.find(t => t.id === activeTab)?.desc}
                      </p>
                    </div>
                  </div>
                </div>

                {activeTab === 'map'    && <WorldMap data={data.worldMap} />}
                {activeTab === 'hops'  && <HopsPerISP data={data.hopsPerISP} />}
                {activeTab === 'rtt'   && <RTTHeatmap data={data.rttPerISP} />}
                {activeTab === 'as'    && <CommonAS data={data.commonAS} />}
                {activeTab === 'exit'  && <HopsToExitAS data={data.hopsToExitAS} />}
                {activeTab === 'border' && <CountryExit data={data.countryExit} />}
              </div>

              {/* Quick nav cards at bottom */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {TABS.filter(t => t.id !== activeTab).map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className="glass-card p-4 text-left hover:bg-white/5 transition-all group"
                  >
                    <div className="text-xl mb-2">{tab.icon}</div>
                    <p className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">{tab.label}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{tab.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
