import { COLORS } from '../../constants/colors';

type CardColor = 'red' | 'green' | 'gold' | 'default';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  delta?: string | number;
  deltaLabel?: string;
  color?: CardColor;
  onClick?: () => void;
  suffix?: string;
}

const colorMap: Record<CardColor, string> = {
  red: COLORS.chartRed,
  green: COLORS.chartGreen,
  gold: COLORS.chartGold,
  default: COLORS.textPrimary,
};

export default function StatCard({
  title,
  value,
  subtitle,
  delta,
  deltaLabel,
  color = 'default',
  onClick,
  suffix,
}: StatCardProps) {
  const valueColor = colorMap[color];

  return (
    <div
      onClick={onClick}
      style={{
        background: COLORS.bgCard,
        borderRadius: 8,
        padding: '16px 20px',
        flex: 1,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s',
        border: '1px solid transparent',
        userSelect: 'none',
      }}
      onMouseEnter={(e) => {
        if (onClick) {
          (e.currentTarget as HTMLDivElement).style.background = COLORS.bgHover;
          (e.currentTarget as HTMLDivElement).style.border = '1px solid #3d4255';
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)';
        }
      }}
      onMouseLeave={(e) => {
        if (onClick) {
          (e.currentTarget as HTMLDivElement).style.background = COLORS.bgCard;
          (e.currentTarget as HTMLDivElement).style.border = '1px solid transparent';
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
        }
      }}
    >
      <div style={{ fontSize: 12, color: COLORS.textSecondary, marginBottom: 8 }}>{title}</div>
      <div
        style={{
          fontSize: 36,
          fontWeight: 700,
          color: valueColor,
          fontVariantNumeric: 'tabular-nums',
          fontFamily: "'DM Mono', 'Roboto Mono', monospace",
          lineHeight: 1.1,
          marginBottom: 6,
        }}
      >
        {value}
        {suffix && (
          <span style={{ fontSize: 14, fontWeight: 400, color: COLORS.textSecondary, marginLeft: 4 }}>
            {suffix}
          </span>
        )}
      </div>
      {(subtitle || delta !== undefined) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {subtitle && (
            <span style={{ fontSize: 12, color: COLORS.textMuted }}>{subtitle}</span>
          )}
          {delta !== undefined && (
            <span
              style={{
                fontSize: 11,
                color: Number(delta) >= 0 ? COLORS.rise : COLORS.fall,
                background: Number(delta) >= 0 ? 'rgba(231,76,60,0.1)' : 'rgba(39,174,96,0.1)',
                borderRadius: 3,
                padding: '1px 5px',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {Number(delta) >= 0 ? '+' : ''}{delta} {deltaLabel}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
