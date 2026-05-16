import { Descriptions, Tag, Divider } from 'antd';
import type { StockRow } from '../../types';
import { COLORS } from '../../constants/colors';
import { formatAmount, formatChangePct, formatMarketCap } from '../../utils/format';
import TrendBadge from './TrendBadge';

interface StockMiniCardProps {
  stock: StockRow;
}

export default function StockMiniCard({ stock }: StockMiniCardProps) {
  return (
    <div style={{ width: 300, padding: 4 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.textPrimary }}>
            {stock.name}
          </div>
          <div style={{ fontSize: 12, color: COLORS.textSecondary }}>
            {stock.code} · {stock.market}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div
            style={{
              fontSize: 20,
              fontWeight: 700,
              color: stock.changePct >= 0 ? COLORS.rise : COLORS.fall,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {stock.price.toFixed(2)}
          </div>
          <TrendBadge
            changePct={stock.changePct}
            limitUp={stock.limitUp}
            limitDown={stock.limitDown}
          />
        </div>
      </div>

      {/* Tags */}
      {stock.description?.tags && (
        <div style={{ marginBottom: 8 }}>
          {stock.description.tags.map((tag, i) => (
            <Tag key={i} color={tag.color} style={{ fontSize: 11 }}>
              {tag.text}
            </Tag>
          ))}
        </div>
      )}

      {/* Summary */}
      {stock.description?.summary && (
        <div
          style={{
            fontSize: 12,
            color: COLORS.textSecondary,
            lineHeight: 1.6,
            background: '#252836',
            borderRadius: 4,
            padding: '6px 8px',
            marginBottom: 8,
          }}
        >
          {stock.description.summary}
        </div>
      )}

      <Divider style={{ margin: '8px 0', borderColor: '#252836' }} />

      {/* Stats */}
      <Descriptions column={2} size="small" labelStyle={{ color: COLORS.textMuted, fontSize: 11 }}
        contentStyle={{ color: COLORS.textPrimary, fontSize: 11, fontVariantNumeric: 'tabular-nums' }}>
        <Descriptions.Item label="涨跌额">
          <span style={{ color: stock.changePct >= 0 ? COLORS.rise : COLORS.fall }}>
            {formatChangePct(stock.change)}
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="成交额">{formatAmount(stock.amount)}</Descriptions.Item>
        <Descriptions.Item label="换手率">{stock.turnoverRate.toFixed(2)}%</Descriptions.Item>
        <Descriptions.Item label="市值">{formatMarketCap(stock.marketCap)}</Descriptions.Item>
        <Descriptions.Item label="今开">{stock.openPrice.toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="昨收">{stock.prevClose.toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="最高">{stock.highPrice.toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="最低">{stock.lowPrice.toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="PE">{stock.pe > 0 ? stock.pe.toFixed(1) : '-'}</Descriptions.Item>
        <Descriptions.Item label="PB">{stock.pb.toFixed(2)}</Descriptions.Item>
      </Descriptions>

      {stock.lianbanCount && stock.lianbanCount > 0 ? (
        <div
          style={{
            marginTop: 8,
            textAlign: 'center',
            background: 'rgba(192,57,43,0.15)',
            border: '1px solid rgba(192,57,43,0.4)',
            borderRadius: 4,
            padding: '4px 0',
            fontSize: 12,
            color: COLORS.limitUp,
            fontWeight: 600,
          }}
        >
          🔥 {stock.lianbanCount}连板 · {stock.description?.limitUpHistory}
        </div>
      ) : null}
    </div>
  );
}
