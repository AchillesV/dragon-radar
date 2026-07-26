import { useState, useCallback, useEffect } from 'react';
import { Table, Button, Popover, Tag, Badge, Tooltip, Space, Dropdown, Checkbox, message } from 'antd';
import { useIsMobile } from '../../hooks/useIsMobile';
import type { ColumnType } from 'antd/es/table';
import {
  LineChartOutlined,
  FileTextOutlined,
  SettingOutlined,
  DownloadOutlined,
  BarChartOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import type { StockRow, AnomalyType, BulkAnalysisResult, TrendStock } from '../../types';
import { COLORS } from '../../constants/colors';
import { formatAmount, formatChangePct, formatMarketCap } from '../../utils/format';
import TrendBadge from '../common/TrendBadge';
import SectorTag from '../common/SectorTag';
import StockMiniCard from '../common/StockMiniCard';
import ReportModal from './ReportModal';
import BulkAnalysisModal from './BulkAnalysisModal';
import { generateStockReport, fetchBulkAnalysis } from '../../api/client';
import { useAppStore } from '../../store';

interface StockTableProps {
  // Accept both StockRow[] and TrendStock[] data types
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  stocks: any[];
  loading?: boolean;
  mode?: 'screening' | 'anomaly' | 'trend';
  anomalyType?: AnomalyType;
  showOperationGuide?: boolean;
}

// ── 复制工具函数（兼容 HTTP / HTTPS） ──
function copyToClipboard(text: string, label: string) {
  try {
    // 优先使用 Clipboard API（需 HTTPS）
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

  // 降级方案：textarea + execCommand（HTTP 环境可用）
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

/** 股票代码行内复制图标 */
function CopyCodeIcon({ code }: { code: string }) {
  return (
    <CopyOutlined
      style={{
        fontSize: 11,
        color: COLORS.textMuted,
        cursor: 'pointer',
        opacity: 0.6,
        transition: 'opacity 0.2s',
      }}
      onClick={(e) => {
        e.stopPropagation();
        copyToClipboard(code, `代码 ${code}`);
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = '0.6'; }}
    />
  );
}

const actionColors: Record<string, string> = {
  '跟进': COLORS.chartRed,
  '低吸': COLORS.rise,
  '观察': COLORS.chartGold,
  '谨慎': COLORS.chartGold,
  '回避': COLORS.fall,
};

const OPTIONAL_COLUMNS = ['pe', 'marketCap', 'description', 'operationGuide'];

// ── 格式化成交量 ──
function formatVolume(v: number): string {
  if (v >= 100000000) return `${(v / 100000000).toFixed(2)}亿`;
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万`;
  return v.toFixed(0);
}

export default function StockTable({
  stocks: initialStocks,
  loading,
  mode = 'screening',
  showOperationGuide = false,
}: StockTableProps) {
  const { hiddenColumns, toggleColumn } = useAppStore();
  const isMobile = useIsMobile();
  const [stocks, setStocks] = useState<unknown[]>(initialStocks);
  const [reportModal, setReportModal] = useState<{
    open: boolean;
    report: StockRow['report'] | null;
  }>({ open: false, report: null });
  const [bulkModal, setBulkModal] = useState<{
    open: boolean;
    result: BulkAnalysisResult | null;
    loading: boolean;
  }>({ open: false, result: null, loading: false });
  const [pageSize, setPageSize] = useState(20);
  const [currentPage, setCurrentPage] = useState(1);

  const isTrendMode = mode === 'trend';

  useEffect(() => {
    setStocks(initialStocks);
    setCurrentPage(1);
  }, [initialStocks]);

  const handleAnalyze = useCallback(async (record: StockRow) => {
    setStocks((prev: unknown[]) =>
      prev.map((s) => {
        const r = s as StockRow;
        return r.code === record.code ? { ...r, analysisLoading: true } : s;
      })
    );
    try {
      const report = await generateStockReport(record.code, record.name);
      setStocks((prev: unknown[]) =>
        prev.map((s) => {
          const r = s as StockRow;
          return r.code === record.code
            ? { ...r, analysisLoading: false, reportGenerated: true, report }
            : s;
        })
      );
      message.success(`${record.name} 分析完成`);
    } catch {
      setStocks((prev: unknown[]) =>
        prev.map((s) => {
          const r = s as StockRow;
          return r.code === record.code ? { ...r, analysisLoading: false } : s;
        })
      );
      message.error('分析失败，请重试');
    }
  }, []);

  const handleBulkAnalysis = async () => {
    setBulkModal({ open: true, result: null, loading: true });
    try {
      const codes = (stocks as StockRow[]).map((s) => s.code);
      const result = await fetchBulkAnalysis(codes);
      setBulkModal({ open: true, result, loading: false });
    } catch {
      setBulkModal({ open: false, result: null, loading: false });
      message.error('整体分析失败，请重试');
    }
  };

  const handleExportCSV = () => {
    if (isTrendMode) {
      const trendStocks = stocks as TrendStock[];
      const headers = ['代码', '名称', '现价', '涨跌幅', '涨跌额', '放量日', '量比', '横盘窗口', '横盘涨幅'];
      const rows = trendStocks.map((s) => [
        s.code,
        s.name,
        s.price?.toFixed(2) ?? '-',
        formatChangePct(s.changePct),
        s.change?.toFixed(2) ?? '-',
        s.breakoutDate,
        s.baselineAvgVolume > 0 ? `${(s.breakoutVolume / s.baselineAvgVolume).toFixed(1)}x` : '-',
        s.rangeWindow,
        `${s.rangeChangePct >= 0 ? '+' : ''}${s.rangeChangePct.toFixed(2)}%`,
      ]);
      const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
      const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `趋势信号_${new Date().toLocaleDateString()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }

    const stockRows = stocks as StockRow[];
    const headers = ['代码', '名称', '价格', '涨跌幅', '成交额(亿)', '换手率', '市值(亿)'];
    const rows = stockRows.map((s) => [
      s.code,
      s.name,
      s.price.toFixed(2),
      formatChangePct(s.changePct),
      (s.amount / 10000).toFixed(2),
      `${s.turnoverRate.toFixed(2)}%`,
      s.marketCap.toFixed(0),
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `龙头雷达_${new Date().toLocaleDateString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── 趋势模式专属列 ──
  const trendColumns: ColumnType<TrendStock>[] = [
    {
      title: '股票',
      key: 'stock',
      width: 130,
      fixed: 'left' as const,
      render: (_: unknown, record: TrendStock) => (
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
      title: '现价/今日涨跌',
      key: 'price',
      width: 120,
      render: (_: unknown, record: TrendStock) => (
        <div>
          <div style={{ fontVariantNumeric: 'tabular-nums', color: COLORS.textPrimary }}>
            {record.price?.toFixed(2) ?? '-'}
          </div>
          {record.change !== undefined && (
            <div style={{ color: record.change >= 0 ? COLORS.rise : COLORS.fall, fontSize: 11, fontVariantNumeric: 'tabular-nums' }}>
              {record.change >= 0 ? '+' : ''}{record.change.toFixed(2)}
            </div>
          )}
          <div style={{ color: record.changePct >= 0 ? COLORS.rise : COLORS.fall, fontSize: 12 }}>
            {record.changePct >= 0 ? '+' : ''}{record.changePct.toFixed(2)}%
          </div>
        </div>
      ),
    },
    {
      title: '放量启动日',
      key: 'breakout',
      width: 180,
      render: (_: unknown, record: TrendStock) => {
        const ratio = record.baselineAvgVolume > 0 ? record.breakoutVolume / record.baselineAvgVolume : 0;
        return (
          <div>
            <div style={{ color: COLORS.textSecondary, fontSize: 12 }}>{record.breakoutDate}</div>
            <Tooltip title={`放量当日成交量 ${formatVolume(record.breakoutVolume)}，放量前5日基准均量 ${formatVolume(record.baselineAvgVolume)}`}>
              <Tag color="volcano" style={{ marginTop: 2, fontSize: 11 }}>量比 {ratio.toFixed(1)}x</Tag>
            </Tooltip>
          </div>
        );
      },
    },
    {
      title: '横盘',
      key: 'range',
      width: 140,
      render: (_: unknown, record: TrendStock) => (
        <div>
          <Tag color="blue" style={{ fontSize: 11 }}>{record.rangeWindow}</Tag>
          <div style={{ fontSize: 11, marginTop: 4, color: COLORS.textSecondary }}>
            累计涨跌幅 {record.rangeChangePct >= 0 ? '+' : ''}{record.rangeChangePct.toFixed(2)}%
          </div>
        </div>
      ),
    },
    {
      title: '说明',
      key: 'description',
      width: 200,
      render: (_: unknown, record: TrendStock) => (
        <span style={{ fontSize: 11, color: COLORS.textMuted }}>{record.description ?? '-'}</span>
      ),
    },
  ];

  // ── 常规模式列（screening / anomaly） ──
  const baseColumns: ColumnType<StockRow>[] = [
    {
      title: '股票',
      key: 'stock',
      width: 130,
      fixed: 'left' as const,
      render: (_: unknown, record: StockRow) => (
        <Popover
          content={<StockMiniCard stock={record} />}
          trigger="click"
          overlayInnerStyle={{ background: COLORS.bgCard, border: '1px solid #3d4255', borderRadius: 8, padding: 0 }}
        >
          <div style={{ cursor: 'pointer' }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.textPrimary }}>
              {record.name}
            </div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: 11, color: COLORS.textMuted }}>{record.code} · {record.market}</span>
              <CopyCodeIcon code={record.code} />
            </div>
            {record.lianbanCount && record.lianbanCount > 0 ? (
              <Badge
                count={`${record.lianbanCount}板`}
                style={{
                  backgroundColor: record.lianbanCount >= 5 ? COLORS.chartGold : COLORS.limitUp,
                  fontSize: 10,
                }}
              />
            ) : null}
          </div>
        </Popover>
      ),
    },
    {
      title: '涨跌幅',
      dataIndex: 'changePct',
      key: 'changePct',
      width: 90,
      sorter: (a: StockRow, b: StockRow) => a.changePct - b.changePct,
      render: (_: unknown, record: StockRow) => (
        <div>
          <TrendBadge
            changePct={record.changePct}
            limitUp={record.limitUp}
            limitDown={record.limitDown}
          />
          <div style={{ fontSize: 11, color: COLORS.textMuted, marginTop: 2, fontVariantNumeric: 'tabular-nums' }}>
            {record.price.toFixed(2)}
          </div>
        </div>
      ),
    },
    {
      title: '成交额',
      dataIndex: 'amount',
      key: 'amount',
      width: 90,
      sorter: (a: StockRow, b: StockRow) => a.amount - b.amount,
      render: (amount: number) => (
        <span style={{ color: COLORS.textPrimary, fontVariantNumeric: 'tabular-nums' }}>
          {formatAmount(amount)}
        </span>
      ),
    },
    {
      title: '换手率',
      dataIndex: 'turnoverRate',
      key: 'turnoverRate',
      width: 80,
      sorter: (a: StockRow, b: StockRow) => a.turnoverRate - b.turnoverRate,
      render: (v: number) => (
        <span
          style={{
            color: v >= 10 ? COLORS.rise : COLORS.textSecondary,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {v.toFixed(2)}%
        </span>
      ),
    },
  ];

  const optionalColumns: ColumnType<StockRow>[] = [
    {
      title: 'PE/PB',
      key: 'pe',
      width: 80,
      render: (_: unknown, record: StockRow) => (
        <div style={{ fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>
          <div style={{ color: COLORS.textSecondary }}>{record.pe > 0 ? record.pe.toFixed(1) : '-'}</div>
          <div style={{ color: COLORS.textMuted }}>{record.pb.toFixed(2)}</div>
        </div>
      ),
    },
    {
      title: '市值',
      dataIndex: 'marketCap',
      key: 'marketCap',
      width: 80,
      sorter: (a: StockRow, b: StockRow) => a.marketCap - b.marketCap,
      render: (cap: number) => (
        <span style={{ color: COLORS.textSecondary, fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>
          {formatMarketCap(cap)}
        </span>
      ),
    },
    {
      title: '标签/描述',
      key: 'description',
      width: 220,
      render: (_: unknown, record: StockRow) => (
        <div>
          {record.description?.tags && (
            <div style={{ marginBottom: 4 }}>
              {record.description.tags.map((tag, i) => (
                <SectorTag key={i} text={tag.text} color={tag.color} />
              ))}
            </div>
          )}
          {record.description?.summary && (
            <Tooltip title={record.description.summary}>
              <div
                style={{
                  fontSize: 11,
                  color: COLORS.textMuted,
                  overflow: 'hidden',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  lineHeight: 1.5,
                }}
              >
                {record.description.summary}
              </div>
            </Tooltip>
          )}
        </div>
      ),
    },
  ];

  const guideColumn: ColumnType<StockRow> = {
    title: '操作建议',
    key: 'operationGuide',
    width: 150,
    render: (_: unknown, record: StockRow) => {
      if (!record.operationGuide) return <span style={{ color: COLORS.textMuted }}>-</span>;
      const { highOpen, lowOpen } = record.operationGuide;
      return (
        <div style={{ fontSize: 11 }}>
          <div style={{ marginBottom: 4 }}>
            <span style={{ color: COLORS.textMuted }}>高开：</span>
            <span
              style={{
                color: actionColors[highOpen.action] ?? COLORS.textSecondary,
                fontWeight: 600,
              }}
            >
              {highOpen.action}
            </span>
            <span style={{ color: COLORS.textMuted }}> {highOpen.position}</span>
          </div>
          <div>
            <span style={{ color: COLORS.textMuted }}>低开：</span>
            <span
              style={{
                color: actionColors[lowOpen.action] ?? COLORS.textSecondary,
                fontWeight: 600,
              }}
            >
              {lowOpen.action}
            </span>
            <span style={{ color: COLORS.textMuted }}> {lowOpen.position}</span>
          </div>
        </div>
      );
    },
  };

  const actionColumn: ColumnType<StockRow> = {
    title: '操作',
    key: 'action',
    width: 140,
    fixed: 'right' as const,
    render: (_: unknown, record: StockRow) => {
      const current = (stocks as StockRow[]).find((s) => s.code === record.code) ?? record;
      return (
        <Space size={6}>
          <Button
            size="small"
            icon={<LineChartOutlined />}
            loading={current.analysisLoading}
            onClick={() => handleAnalyze(current)}
            style={{
              fontSize: 11,
              background: 'rgba(24,144,255,0.12)',
              borderColor: 'rgba(24,144,255,0.3)',
              color: COLORS.chartBlue,
            }}
          >
            分析
          </Button>
          <Button
            size="small"
            icon={<FileTextOutlined />}
            disabled={!current.reportGenerated}
            onClick={() => current.report && setReportModal({ open: true, report: current.report })}
            style={{
              fontSize: 11,
              background: current.reportGenerated
                ? 'rgba(24,144,255,0.12)'
                : 'transparent',
              borderColor: current.reportGenerated
                ? 'rgba(24,144,255,0.3)'
                : '#3d4255',
              color: current.reportGenerated ? COLORS.chartBlue : COLORS.textMuted,
            }}
          >
            报告
          </Button>
        </Space>
      );
    },
  };

  // Build final columns based on mode
  let columns: ColumnType<Record<string, unknown>>[];

  if (isTrendMode) {
    columns = trendColumns as unknown as ColumnType<Record<string, unknown>>[];
  } else {
    const visibleOptional = optionalColumns.filter(
      (col) => !hiddenColumns.includes(String(col.key))
    );
    columns = [
      ...baseColumns,
      ...visibleOptional,
      ...(showOperationGuide && !hiddenColumns.includes('operationGuide') ? [guideColumn] : []),
      ...(isMobile ? [] : [actionColumn]),
    ] as unknown as ColumnType<Record<string, unknown>>[];
  }

  // Column settings (only for non-trend)
  const columnSettingsItems = isTrendMode ? [] : OPTIONAL_COLUMNS.map((col) => {
    const labels: Record<string, string> = {
      pe: 'PE/PB',
      marketCap: '市值',
      description: '标签/描述',
      operationGuide: '操作建议',
    };
    return {
      key: col,
      label: (
        <Checkbox checked={!hiddenColumns.includes(col)} onChange={() => toggleColumn(col)}>
          <span style={{ color: COLORS.textSecondary }}>{labels[col]}</span>
        </Checkbox>
      ),
    };
  });

  const handleCopyAll = () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const text = (stocks as any[])
      .map((s) => `${s.name}(${s.code})`)
      .join('\n');
    copyToClipboard(text, `全部 ${stocks.length} 只股票`);
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Table toolbar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <div style={{ fontSize: 13, color: COLORS.textSecondary }}>
          共 <span style={{ color: COLORS.textPrimary, fontWeight: 600 }}>{stocks.length}</span> 只
        </div>
        <Space wrap>
          <Button
            size="small"
            icon={<CopyOutlined />}
            onClick={handleCopyAll}
            style={{ borderColor: COLORS.chartBlue, color: COLORS.chartBlue, background: 'rgba(24,144,255,0.08)', fontSize: 12 }}
          >
            复制全部
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={handleExportCSV}
            style={{ borderColor: '#3d4255', color: COLORS.textMuted, background: 'transparent', fontSize: 12 }}
          >
            导出CSV
          </Button>
          {!isTrendMode && (
            <Dropdown
              menu={{ items: columnSettingsItems }}
              trigger={['click']}
              overlayStyle={{ minWidth: 160 }}
            >
              <Button
                size="small"
                icon={<SettingOutlined />}
                style={{ borderColor: '#3d4255', color: COLORS.textMuted, background: 'transparent', fontSize: 12 }}
              >
                列设置
              </Button>
            </Dropdown>
          )}
        </Space>
      </div>

      <Table<Record<string, unknown>>
        columns={columns}
        dataSource={stocks as Record<string, unknown>[]}
        rowKey="code"
        loading={loading}
        size="small"
        scroll={{ x: isTrendMode ? 800 : 900 }}
        pagination={{
          current: currentPage,
          pageSize,
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50', '100'],
          showTotal: (total) => `共 ${total} 条`,
          style: { color: COLORS.textSecondary },
          onChange: (page, size) => {
            setCurrentPage(page);
            setPageSize(size);
          },
        }}
        style={{ background: 'transparent' }}
      />

      {/* Sticky bulk analysis button (non-trend only) */}
      {!isTrendMode && (
        <div
          style={{
            position: 'sticky',
            bottom: 24,
            display: 'flex',
            justifyContent: 'center',
            pointerEvents: 'none',
            zIndex: 10,
            marginTop: 8,
          }}
        >
          <Button
            type="primary"
            size="large"
            icon={<BarChartOutlined />}
            onClick={handleBulkAnalysis}
            style={{
              background: COLORS.chartRed,
              borderColor: COLORS.chartRed,
              borderRadius: 24,
              padding: '0 32px',
              height: 44,
              fontSize: 14,
              fontWeight: 600,
              boxShadow: `0 4px 20px rgba(255,77,79,0.4)`,
              pointerEvents: 'auto',
            }}
          >
            整体分析 ({(stocks as StockRow[]).length} 只)
          </Button>
        </div>
      )}

      {/* Modals */}
      <ReportModal
        report={reportModal.report ?? null}
        open={reportModal.open}
        onClose={() => setReportModal({ open: false, report: null })}
      />
      <BulkAnalysisModal
        result={bulkModal.result}
        open={bulkModal.open}
        loading={bulkModal.loading}
        onClose={() => setBulkModal({ open: false, result: null, loading: false })}
      />
    </div>
  );
}
