import { Card, Tag, Tooltip } from 'antd';
import { COLORS } from '../../constants/colors';
import { formatChangePct } from '../../utils/format';
import type { SectorAnalysis } from '../../types';

export function starsOf(score: number): number {
  if (score >= 90) return 5;
  if (score >= 80) return 4;
  if (score >= 70) return 3;
  if (score >= 60) return 2;
  return 1;
}

export function scoreColor(score: number): string {
  if (score >= 85) return COLORS.chartRed;
  if (score >= 70) return COLORS.chartGold;
  if (score >= 55) return COLORS.chartBlue;
  return COLORS.textMuted;
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 52 }}>
      <span style={{ fontSize: 11, color: COLORS.textMuted }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: color ?? COLORS.textPrimary }}>{value}</span>
    </div>
  );
}

function chgColor(v?: number): string {
  if (v === undefined) return COLORS.textMuted;
  return v > 0 ? COLORS.rise : v < 0 ? COLORS.fall : COLORS.textSecondary;
}

export default function SectorHeatCard({
  sector,
  rank,
  onClick,
  compact,
}: {
  sector: SectorAnalysis;
  rank?: number;
  onClick?: () => void;
  compact?: boolean;
}) {
  const s = starsOf(sector.score);
  return (
    <Card
      size="small"
      hoverable={!!onClick}
      onClick={onClick}
      styles={{ body: { padding: compact ? '10px 12px' : '14px 16px' } }}
      style={{
        background: COLORS.bgCard,
        border: `1px solid ${rank === 1 ? COLORS.chartRed : 'var(--c-border)'}`,
        marginBottom: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          {rank !== undefined && (
            <span style={{
              fontSize: 13, fontWeight: 700, color: rank <= 3 ? COLORS.chartRed : COLORS.textMuted,
              minWidth: 18,
            }}>
              {rank}
            </span>
          )}
          <span style={{ fontSize: 15, fontWeight: 700, color: COLORS.textPrimary, whiteSpace: 'nowrap' }}>
            {sector.name}
          </span>
          <Tag
            color={sector.type === 'concept' ? 'magenta' : 'blue'}
            style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}
          >
            {sector.type === 'concept' ? '概念' : '行业'}
          </Tag>
          <span style={{ fontSize: 11, color: COLORS.textMuted }}>
            候选 {sector.candidateCount}
          </span>
        </div>
        <div style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: scoreColor(sector.score), lineHeight: 1 }}>
            {sector.score.toFixed(1)}
          </div>
          <div style={{ fontSize: 11, color: COLORS.chartGold, letterSpacing: 1 }}>
            {'★'.repeat(s)}{'☆'.repeat(5 - s)}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
        <Metric label="今日" value={formatChangePct(sector.changePct)} color={chgColor(sector.changePct)} />
        <Metric label="5日" value={sector.change5Pct === undefined ? '--' : formatChangePct(sector.change5Pct)} color={chgColor(sector.change5Pct)} />
        <Metric label="20日" value={sector.change20Pct === undefined ? '--' : formatChangePct(sector.change20Pct)} color={chgColor(sector.change20Pct)} />
        <Metric label="量比" value={sector.lb === undefined ? '--' : `${sector.lb.toFixed(2)}`} />
        <Tooltip title="今日主力净额 / 成交额（板块级资金）">
          <div style={{ display: 'flex' }}>
            <Metric label="资金" value={sector.netInflowPct === undefined ? '--' : `${sector.netInflowPct > 0 ? '+' : ''}${sector.netInflowPct.toFixed(1)}%`} color={chgColor(sector.netInflowPct)} />
          </div>
        </Tooltip>
        <Metric label="扩散度" value={sector.breadthScore === undefined ? '--' : sector.breadthScore.toFixed(0)} />
        <Metric label="上涨占比" value={sector.upRatio === undefined ? '--' : `${sector.upRatio.toFixed(0)}%`} />
      </div>

      {!compact && sector.signals.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {sector.signals.map((sig) => (
            <Tag key={sig} color="orange" style={{ marginInlineEnd: 0, fontSize: 11 }}>
              {sig}
            </Tag>
          ))}
        </div>
      )}
    </Card>
  );
}
