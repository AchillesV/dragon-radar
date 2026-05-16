import { COLORS } from '../../constants/colors';
import { formatChangePct } from '../../utils/format';

interface TrendBadgeProps {
  changePct: number;
  limitUp?: boolean;
  limitDown?: boolean;
  size?: 'small' | 'default';
}

export default function TrendBadge({ changePct, limitUp, limitDown, size = 'default' }: TrendBadgeProps) {
  let bg: string;
  let color: string;
  let border: string;

  if (limitUp) {
    bg = COLORS.limitUp;
    color = '#fff';
    border = 'none';
  } else if (limitDown) {
    bg = COLORS.limitDown;
    color = '#fff';
    border = 'none';
  } else if (changePct > 0) {
    bg = 'rgba(231,76,60,0.12)';
    color = COLORS.rise;
    border = `1px solid rgba(231,76,60,0.3)`;
  } else if (changePct < 0) {
    bg = 'rgba(39,174,96,0.12)';
    color = COLORS.fall;
    border = `1px solid rgba(39,174,96,0.3)`;
  } else {
    bg = 'rgba(149,165,166,0.12)';
    color = COLORS.neutral;
    border = `1px solid rgba(149,165,166,0.3)`;
  }

  const fontSize = size === 'small' ? 12 : 13;
  const padding = size === 'small' ? '2px 6px' : '3px 8px';

  return (
    <span
      style={{
        display: 'inline-block',
        background: bg,
        color,
        border,
        borderRadius: 4,
        fontSize,
        fontWeight: 600,
        padding,
        fontVariantNumeric: 'tabular-nums',
        whiteSpace: 'nowrap',
      }}
    >
      {limitUp ? '涨停' : limitDown ? '跌停' : formatChangePct(changePct)}
    </span>
  );
}
