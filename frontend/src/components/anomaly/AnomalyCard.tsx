import { Badge, Skeleton } from 'antd';
import { useNavigate } from 'react-router-dom';
import { COLORS } from '../../constants/colors';
import type { AnomalyCard as AnomalyCardType } from '../../types';

interface AnomalyCardProps {
  card: AnomalyCardType;
  loading?: boolean;
}

export default function AnomalyCard({ card, loading }: AnomalyCardProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div
        style={{
          background: COLORS.bgCard,
          borderRadius: 8,
          padding: '16px',
          width: '100%',
          height: 140,
          border: '1px solid #252836',
        }}
      >
        <Skeleton active paragraph={{ rows: 2 }} />
      </div>
    );
  }

  return (
    <Badge count={card.count} color={COLORS.chartRed} size="small" offset={[-8, 8]}>
      <div
        onClick={() => navigate(`/anomaly/${card.id}`)}
        style={{
          background: COLORS.bgCard,
          borderRadius: 8,
          padding: '16px',
          width: '100%',
          height: 140,
          border: `1px solid #252836`,
          cursor: 'pointer',
          transition: 'all 0.25s',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          boxSizing: 'border-box',
        }}
        onMouseEnter={(e) => {
          const el = e.currentTarget as HTMLDivElement;
          el.style.transform = 'translateY(-3px)';
          el.style.borderColor = 'rgba(255,77,79,0.4)';
          el.style.boxShadow = '0 8px 24px rgba(0,0,0,0.3)';
        }}
        onMouseLeave={(e) => {
          const el = e.currentTarget as HTMLDivElement;
          el.style.transform = 'translateY(0)';
          el.style.borderColor = '#252836';
          el.style.boxShadow = 'none';
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 22 }}>{card.icon}</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: COLORS.textPrimary }}>
              {card.title}
            </span>
          </div>
          <div
            style={{
              fontSize: 12,
              color: COLORS.textSecondary,
              lineHeight: 1.6,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {card.description}
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: card.count > 0 ? COLORS.chartRed : COLORS.textMuted,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {card.count}
          </span>
          {card.lastUpdated && (
            <span style={{ fontSize: 11, color: COLORS.textMuted }}>
              {card.lastUpdated}
            </span>
          )}
        </div>
      </div>
    </Badge>
  );
}
