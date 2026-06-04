export function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-6">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-amber-500 animate-spin" />
        <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-blue-500 animate-spin" style={{ animationDuration: '1.5s', animationDirection: 'reverse' }} />
        <div className="absolute inset-4 rounded-full border-2 border-transparent border-t-green-500 animate-spin" style={{ animationDuration: '2s' }} />
      </div>
      <div className="text-center">
        <p className="text-white font-medium">Loading analytics data</p>
        <p className="text-gray-500 text-sm mt-1">Processing RIPE Atlas traceroutes…</p>
      </div>
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-4">
      <div className="text-4xl">⚠️</div>
      <div className="text-center">
        <p className="text-red-400 font-medium">Failed to load data</p>
        <p className="text-gray-500 text-sm mt-1 max-w-md font-mono">{message}</p>
        <p className="text-gray-600 text-xs mt-3">
          Run <code className="text-amber-500">python3 pipeline/run.py</code> first to generate data files.
        </p>
      </div>
    </div>
  )
}

export function EmptyState({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] gap-3">
      <div className="text-gray-700 text-5xl">∅</div>
      <p className="text-gray-500 text-sm">{message ?? 'No data available'}</p>
    </div>
  )
}
