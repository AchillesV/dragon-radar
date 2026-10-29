import { COLORS } from '../../constants/colors';
import type { CoreSector } from '../../types';

interface Props {
  sectors: CoreSector[];
  selected: string | null;
  onSelect: (name: string | null) => void;
  isMobile: boolean;
  variant?: 'hot' | 'watch';
}

function fmtNet(v?: number): string {
  if (v === undefined || v === null) return '—';
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}亿`;
}

function fmtRatio(v?: number): string {
  if (v === undefined || v === null) return '—';
  return `${v.toFixed(2)}x`;
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
      <span style={{ color: COLORS.textMuted }}>{label}</span>
      <span style={{ color: color ?? COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>{value}</span>
    </div>
  );
}

export default function CoreSectorCards({ sectors, selected, onSelect, isMobile, variant = 'hot' }: Props) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(240px, 1fr))',
        gap: 12,
      }}
    >
      {sectors.map((s) => {
        const interactive = variant === 'hot';
        const active = interactive && selected === s.name;
        const netColor =
          s.mainNet5d === undefined || s.mainNet5d === null
            ? COLORS.textMuted
            : s.mainNet5d > 0
              ? COLORS.rise
              : COLORS.fall;
        return (
          <div
            key={s.name}
            onClick={interactive ? () => onSelect(active ? null : s.name) : undefined}
            style={{
              background: active ? 'rgba(255,77,79,0.08)' : COLORS.bgCard,
              border: `${interactive ? '1px solid' : '1px dashed'} ${active ? 'rgba(255,77,79,0.45)' : 'var(--c-border)'}`,
              borderRadius: 8,
              padding: 12,
              cursor: interactive ? 'pointer' : 'default',
              opacity: interactive ? 1 : 0.9,
              transition: 'all 0.2s',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: COLORS.textPrimary }}>
                {s.name}
                <span style={{ fontSize: 11, color: COLORS.textMuted, marginLeft: 6 }}>
                  {s.limitUpCount}只涨停
                </span>
              </span>
              <span style={{ fontSize: 12, fontWeight: 600, color: COLORS.chartGold }}>
                {s.score.toFixed(1)}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', marginBottom: 8 }}>
              <Metric label="最高板" value={`${s.maxBoard}板`} color={COLORS.chartRed} />
              <Metric label="连板数" value={`${s.multiBoardCount}家`} />
              <Metric label="5日净额" value={fmtNet(s.mainNet5d)} color={netColor} />
              <Metric label="放量" value={fmtRatio(s.volumeRatio)} />
              <Metric label="成交额" value={s.amountToday === undefined ? '—' : `${s.amountToday.toFixed(0)}亿`} />
              <Metric
                label="上涨占比"
                value={s.riseRatio === undefined ? '—' : `${(s.riseRatio * 100).toFixed(0)}%`}
              />
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {s.reasons.map((r) => {
                const missing = r.includes('缺失');
                const fail = !interactive && !missing;
                return (
                  <span
                    key={r}
                    style={{
                      fontSize: 11,
                      padding: '1px 6px',
                      borderRadius: 3,
                      color: missing ? COLORS.textMuted : fail ? COLORS.fall : COLORS.textSecondary,
                      background: missing
                        ? 'rgba(139,148,158,0.12)'
                        : fail
                          ? 'rgba(255,77,79,0.12)'
                          : 'rgba(24,144,255,0.12)',
                    }}
                  >
                    {r}
                  </span>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
