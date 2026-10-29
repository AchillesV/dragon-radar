import { Table, Button, Space, message } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import type { ColumnType } from 'antd/es/table';
import { COLORS } from '../../constants/colors';
import { formatChangePct } from '../../utils/format';
import type { CoreStock } from '../../types';

function formatAmountYuan(v?: number): string {
  if (!v) return '—';
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(1)}万`;
  return v.toFixed(0);
}

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
  stocks: CoreStock[];
  loading?: boolean;
}

export default function CoreStockTable({ stocks, loading }: Props) {
  const columns: ColumnType<CoreStock>[] = [
    {
      title: '股票',
      key: 'stock',
      width: 140,
      fixed: 'left' as const,
      render: (_: unknown, record: CoreStock) => (
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
      title: '板块',
      dataIndex: 'sector',
      key: 'sector',
      width: 100,
      render: (v: string) => (
        <span
          style={{
            fontSize: 11,
            color: COLORS.chartBlue,
            background: 'rgba(24,144,255,0.12)',
            border: '1px solid rgba(24,144,255,0.25)',
            borderRadius: 3,
            padding: '1px 6px',
            whiteSpace: 'nowrap',
          }}
        >
          {v}
        </span>
      ),
    },
    {
      title: '现价/涨幅',
      key: 'price',
      width: 120,
      sorter: (a: CoreStock, b: CoreStock) => a.changePct - b.changePct,
      defaultSortOrder: 'descend' as const,
      render: (_: unknown, record: CoreStock) => (
        <div>
          <div style={{ color: COLORS.textPrimary, fontVariantNumeric: 'tabular-nums' }}>
            {record.price?.toFixed(2) ?? '—'}
          </div>
          <div style={{ color: record.changePct >= 0 ? COLORS.rise : COLORS.fall, fontSize: 12 }}>
            {formatChangePct(record.changePct)}
          </div>
        </div>
      ),
    },
    {
      title: '成交额',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      sorter: (a: CoreStock, b: CoreStock) => (a.amount ?? 0) - (b.amount ?? 0),
      render: (v?: number) => (
        <span style={{ color: COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>{formatAmountYuan(v)}</span>
      ),
    },
    {
      title: '封板资金',
      dataIndex: 'sealAmount',
      key: 'sealAmount',
      width: 110,
      sorter: (a: CoreStock, b: CoreStock) => (a.sealAmount ?? 0) - (b.sealAmount ?? 0),
      defaultSortOrder: undefined,
      render: (v?: number) => (
        <span style={{ color: COLORS.chartGold, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
          {formatAmountYuan(v)}
        </span>
      ),
    },
    {
      title: '换手率',
      dataIndex: 'turnoverRate',
      key: 'turnoverRate',
      width: 90,
      sorter: (a: CoreStock, b: CoreStock) => (a.turnoverRate ?? 0) - (b.turnoverRate ?? 0),
      render: (v?: number) => (
        <span style={{ color: COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>
          {v === undefined ? '—' : `${v.toFixed(2)}%`}
        </span>
      ),
    },
    {
      title: '首封时间',
      dataIndex: 'firstLimitTime',
      key: 'firstLimitTime',
      width: 100,
      render: (v?: string) => <span style={{ color: COLORS.textSecondary }}>{v ?? '—'}</span>,
    },
    {
      title: '炸板',
      dataIndex: 'breakCount',
      key: 'breakCount',
      width: 70,
      render: (v: number) => (
        <span style={{ color: v > 0 ? COLORS.fall : COLORS.textMuted, fontVariantNumeric: 'tabular-nums' }}>{v}</span>
      ),
    },
  ];

  const handleCopyAll = () => {
    if (stocks.length === 0) {
      message.warning('暂无可复制的股票');
      return;
    }
    copyToClipboard(stocks.map((s) => `${s.name}(${s.code})`).join('\n'), `全部 ${stocks.length} 只首板`);
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
      <Table<CoreStock>
        columns={columns}
        dataSource={stocks}
        rowKey="code"
        loading={loading}
        size="small"
        scroll={{ x: 900 }}
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
