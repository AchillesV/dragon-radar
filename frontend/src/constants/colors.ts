// CSS variable references — work everywhere (inline styles, className)
// The actual values are set via CSS variables in index.css
export const COLORS = {
  limitUp:       'var(--c-limit-up)',
  rise:          'var(--c-rise)',
  fall:          'var(--c-fall)',
  limitDown:     'var(--c-limit-down)',
  neutral:       'var(--c-neutral)',
  bgPrimary:     'var(--c-bg-primary)',
  bgCard:        'var(--c-bg-card)',
  bgHover:       'var(--c-bg-hover)',
  textPrimary:   'var(--c-text-primary)',
  textSecondary: 'var(--c-text-secondary)',
  textMuted:     'var(--c-text-muted)',
  chartRed:      'var(--c-chart-red)',
  chartGreen:    'var(--c-chart-green)',
  chartBlue:     'var(--c-chart-blue)',
  chartGold:     'var(--c-chart-gold)',
} as const;

// Raw hex values for ECharts canvas rendering (does not support CSS variables)
export const DARK_COLORS_RAW = {
  limitUp: '#c0392b', rise: '#e74c3c', fall: '#27ae60', limitDown: '#1e8449', neutral: '#95a5a6',
  bgPrimary: '#0f1117', bgCard: '#1a1d29', bgHover: '#252836',
  textPrimary: '#ffffff', textSecondary: '#8b949e', textMuted: '#4a5568',
  chartRed: '#ff4d4f', chartGreen: '#52c41a', chartBlue: '#1890ff', chartGold: '#faad14',
  border: '#252836', borderLight: '#3d4255',
} as const;

export const LIGHT_COLORS_RAW = {
  limitUp: '#c0392b', rise: '#e74c3c', fall: '#27ae60', limitDown: '#1e8449', neutral: '#95a5a6',
  bgPrimary: '#f0f2f5', bgCard: '#ffffff', bgHover: '#f5f5f5',
  textPrimary: '#141414', textSecondary: '#595959', textMuted: '#8c8c8c',
  chartRed: '#ff4d4f', chartGreen: '#52c41a', chartBlue: '#1890ff', chartGold: '#faad14',
  border: '#e8e8e8', borderLight: '#d9d9d9',
} as const;

export interface RawColors {
  limitUp: string; rise: string; fall: string; limitDown: string; neutral: string;
  bgPrimary: string; bgCard: string; bgHover: string;
  textPrimary: string; textSecondary: string; textMuted: string;
  chartRed: string; chartGreen: string; chartBlue: string; chartGold: string;
  border: string; borderLight: string;
}
