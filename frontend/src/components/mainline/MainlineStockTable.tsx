import { Table, Tag } from 'antd';
import type { ColumnType } from 'antd/es/table';
import { COLORS } from '../../constants/colors';
import { formatChangePct } from '../../utils/format';
import type { MainlineStock, MainlineSector } from '../../types';

function formatAmountYuan(v?: number): string {
  if (!v) return '-';
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(1)}万`;
  return v.toFixed(0);
}

interface Props {
  stocks: MainlineStock[];
  sectors: MainlineSector[];
  loading?: boolean;
}

export default function MainlineStockTable({ stocks, sectors, loading }: Props) {
  const sectorName = (id: string) => sectors.find((s) => s.id === id)?.name ?? id;

  const columns: ColumnType<MainlineStock>[] = [
    {
      title: '股票',
      key: 'stock',
      width: 130,
      fixed: 'left' as const,
      render: (_: unknown, record: MainlineStock) => (
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.textPrimary }}>{record.name}</div>
          <div style={{ fontSize: 11, color: COLORS.textMuted }}>{record.code}</div>
        </div>
      ),
    },
    {
      title: '所属子板块',
      key: 'subsectors',
      width: 220,
      render: (_: unknown, record: MainlineStock) => (
        <div>
          {record.subsectors.map((id) => (
            <Tag key={id} color="geekblue" style={{ fontSize: 11, marginBottom: 2 }}>
              {sectorName(id)}
            </Tag>
          ))}
        </div>
      ),
    },
    {
      title: '现价/今日涨跌幅',
      key: 'price',
      width: 130,
      sorter: (a: MainlineStock, b: MainlineStock) => a.changePct - b.changePct,
      defaultSortOrder: 'descend' as const,
      render: (_: unknown, record: MainlineStock) => (
        <div>
          <div style={{ fontVariantNumeric: 'tabular-nums', color: COLORS.textPrimary }}>
            {record.price?.toFixed(2) ?? '-'}
          </div>
          <div style={{ color: record.changePct >= 0 ? COLORS.rise : COLORS.fall, fontSize: 12 }}>
            {formatChangePct(record.changePct)}
          </div>
        </div>
      ),
    },
    {
      title: '今日成交额',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      sorter: (a: MainlineStock, b: MainlineStock) => (a.amount ?? 0) - (b.amount ?? 0),
      render: (v: number | undefined) => (
        <span style={{ color: COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>{formatAmountYuan(v)}</span>
      ),
    },
    {
      title: '4/1~6/30 累计涨幅',
      dataIndex: 'periodGainPct',
      key: 'periodGainPct',
      width: 140,
      sorter: (a: MainlineStock, b: MainlineStock) => a.periodGainPct - b.periodGainPct,
      render: (v: number) => (
        <span style={{ color: COLORS.chartRed, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
          +{v.toFixed(1)}%
        </span>
      ),
    },
  ];

  return (
    <Table<MainlineStock>
      columns={columns}
      dataSource={stocks}
      rowKey="code"
      loading={loading}
      size="small"
      scroll={{ x: 700 }}
      pagination={{
        pageSize: 20,
        showSizeChanger: true,
        pageSizeOptions: ['10', '20', '50', '100'],
        showTotal: (total) => `共 ${total} 只`,
        style: { color: COLORS.textSecondary },
      }}
      style={{ background: 'transparent' }}
    />
  );
}
