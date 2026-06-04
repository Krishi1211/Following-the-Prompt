interface Props {
  label: string
  value: string | number
  sub?: string
  accentColor?: string
  icon?: React.ReactNode
}

export function StatCard({ label, value, sub, accentColor, icon }: Props) {
  return (
    <div className="glass-card p-5 flex flex-col gap-2 relative overflow-hidden">
      {accentColor && (
        <div
          className="absolute top-0 left-0 right-0 h-0.5 rounded-t-xl"
          style={{ background: accentColor }}
        />
      )}
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</span>
        {icon && <span className="text-gray-600">{icon}</span>}
      </div>
      <div className="stat-number" style={accentColor ? { color: accentColor } : {}}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      {sub && <span className="text-xs text-gray-500">{sub}</span>}
    </div>
  )
}
