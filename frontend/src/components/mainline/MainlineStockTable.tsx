import { Table, Button, Space, message } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import type { ColumnType } from 'antd/es/table';
import { COLORS } from '../../constants/colors';
import { formatChangePct } from '../../utils/format';
import type { MainlineStock } from '../../types';

function formatAmountYuan(v?: number): string {
  if (!v) return '-';
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(1)}万`;
  return v.toFixed(0);
}

// 复制工具函数（兼容 HTTP / HTTPS，与 screening/StockTable.tsx 保持一致）
function copyToClipboard(text: string, label: string) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(
        () => message.success(`${label} 已复制`),
        () => { throw new Error('clipboard API rejected'); },
      );
      return;
    }
  } catch {
    // fall through to legacy method
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  textarea.style.top = '-9999px';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    document.execCommand('copy');
    message.success(`${label} 已复制`);
  } catch {
    message.error('复制失败，请手动复制');
  }
  document.body.removeChild(textarea);
}

function CopyCodeIcon({ code }: { code: string }) {
  return (
    <CopyOutlined
      style={{ fontSize: 11, color: COLORS.textMuted, cursor: 'pointer', opacity: 0.6 }}
      onClick={(e) => {
        e.stopPropagation();
        copyToClipboard(code, `代码 ${code}`);
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = '0.6'; }}
    />
  );
}

interface Props {
  stocks: MainlineStock[];
  loading?: boolean;
}

export default function MainlineStockTable({ stocks, loading }: Props) {
  const columns: ColumnType<MainlineStock>[] = [
    {
      title: '股票',
      key: 'stock',
      width: 130,
      fixed: 'left' as const,
      render: (_: unknown, record: MainlineStock) => (
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.textPrimary }}>{record.name}</div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <span style={{ fontSize: 11, color: COLORS.textMuted }}>{record.code}</span>
            <CopyCodeIcon code={record.code} />
          </div>
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

  const handleCopyAll = () => {
    if (stocks.length === 0) {
      message.warning('暂无可复制的股票');
      return;
    }
    const text = stocks.map((s) => `${s.name}(${s.code})`).join('\n');
    copyToClipboard(text, `全部 ${stocks.length} 只核心票`);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
        <Space>
          <Button
            size="small"
            icon={<CopyOutlined />}
            onClick={handleCopyAll}
            style={{ borderColor: COLORS.chartBlue, color: COLORS.chartBlue, background: 'rgba(24,144,255,0.08)', fontSize: 12 }}
          >
            复制全部
          </Button>
        </Space>
      </div>
      <Table<MainlineStock>
        columns={columns}
        dataSource={stocks}
        rowKey="code"
        loading={loading}
        size="small"
        scroll={{ x: 600 }}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50', '100'],
          showTotal: (total) => `共 ${total} 只`,
          style: { color: COLORS.textSecondary },
        }}
        style={{ background: 'transparent' }}
      />
    </div>
  );
}
