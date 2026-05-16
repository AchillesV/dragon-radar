import { Badge, Popover } from 'antd';
import { COLORS } from '../../constants/colors';
import { useLianbanTiers } from '../../hooks/useMarketData';
import { LoadingState } from '../common/StatusStates';
import StockMiniCard from '../common/StockMiniCard';
import { mockStocks } from '../../mock/data';

export default function LianbanTier() {
  const { data: tiers, isLoading } = useLianbanTiers();

  if (isLoading) return <LoadingState height={160} />;
  if (!tiers) return null;

  return (
    <div style={{ background: COLORS.bgCard, borderRadius: 8, padding: '16px' }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.textPrimary, marginBottom: 12 }}>
        连板梯队
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {tiers.map((tier) => (
          <div key={tier.count} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Tier label */}
            <div
              style={{
                minWidth: 48,
                textAlign: 'center',
                fontSize: 13,
                fontWeight: 700,
                color: tier.count >= 8 ? COLORS.chartGold : tier.count >= 5 ? COLORS.limitUp : COLORS.rise,
                background:
                  tier.count >= 8
                    ? 'rgba(250,173,20,0.12)'
                    : tier.count >= 5
                    ? 'rgba(192,57,43,0.12)'
                    : 'rgba(231,76,60,0.08)',
                borderRadius: 6,
                padding: '4px 0',
                border:
                  tier.count >= 8
                    ? `1px solid rgba(250,173,20,0.4)`
                    : tier.count >= 5
                    ? `1px solid rgba(192,57,43,0.4)`
                    : `1px solid rgba(231,76,60,0.2)`,
                flexShrink: 0,
              }}
            >
              {tier.count}板
            </div>

            {/* Stocks */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {tier.stocks.map((stock, idx) => {
                const fullStock = mockStocks.find((s) => s.code === stock.code);
                const isTop = idx === 0 && tier === tiers[0];

                const card = (
                  <div
                    key={stock.code}
                    style={{
                      background: isTop ? 'rgba(250,173,20,0.08)' : COLORS.bgHover,
                      border: isTop
                        ? `1px solid rgba(250,173,20,0.5)`
                        : `1px solid #3d4255`,
                      borderRadius: 6,
                      padding: '5px 10px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 2,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: COLORS.textPrimary }}>
                        {stock.name}
                      </span>
                      <Badge
                        count={tier.count}
                        style={{
                          backgroundColor: tier.count >= 8 ? COLORS.chartGold : COLORS.limitUp,
                          fontSize: 10,
                          minWidth: 18,
                          height: 16,
                          lineHeight: '16px',
                          padding: '0 4px',
                        }}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <span style={{ fontSize: 11, color: COLORS.textMuted }}>{stock.code}</span>
                      {stock.limitUpReason && (
                        <span style={{ fontSize: 11, color: COLORS.chartGold }}>
                          {stock.limitUpReason}
                        </span>
                      )}
                    </div>
                  </div>
                );

                if (fullStock) {
                  return (
                    <Popover
                      key={stock.code}
                      content={<StockMiniCard stock={fullStock} />}
                      trigger="click"
                      overlayStyle={{ maxWidth: 340 }}
                      overlayInnerStyle={{ background: COLORS.bgCard, border: '1px solid #3d4255', borderRadius: 8 }}
                    >
                      {card}
                    </Popover>
                  );
                }
                return card;
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
