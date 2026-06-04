import type { LLM } from '../types/analytics'

const CONFIG: Record<LLM, { color: string; bg: string; label: string }> = {
  Claude:  { color: '#D97706', bg: 'rgba(217,119,6,0.15)',  label: 'Claude'  },
  Gemini:  { color: '#2563EB', bg: 'rgba(37,99,235,0.15)',  label: 'Gemini'  },
  ChatGPT: { color: '#16A34A', bg: 'rgba(22,163,74,0.15)', label: 'ChatGPT' },
}

interface Props {
  llm: LLM
  size?: 'sm' | 'md'
}

export function LLMBadge({ llm, size = 'md' }: Props) {
  const cfg = CONFIG[llm]
  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${padding}`}
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}40` }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: cfg.color }}
      />
      {cfg.label}
    </span>
  )
}

export const LLM_COLORS: Record<string, string> = {
  Claude:  '#D97706',
  Gemini:  '#2563EB',
  ChatGPT: '#16A34A',
}
