import { useMemo, useState } from 'react';
import { Table, Select, Button, Space, message, Tag, Tabs } from 'antd';
import { SyncOutlined, TrophyOutlined, CopyOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnType } from 'antd/es/table';
import { useBoardPreselection, useBoardPicks, useBoardDates, useSyncBoardPicks } from '../hooks/useBoardData';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';
import { formatChangePct } from '../utils/format';
import { LoadingState, EmptyState, ErrorState } from '../components/common/StatusStates';
import BoardBacktestView from '../components/board/BoardBacktestView';
import type { BoardPick } from '../types';

function formatVolume(v?: number): string {
  if (v === undefined || v === null) return '—';
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万手`;
  return `${v.toFixed(0)}手`;
}

function stageBadge(stage: 'pre' | 'final') {
  return stage === 'pre' ? (
    <Tag color="gold" style={{ margin: 0 }}>预选</Tag>
  ) : (
    <Tag color="red" style={{ margin: 0 }}>最终</Tag>
  );
}

export default function Board() {
  const isMobile = useIsMobile();
  const [activeTab, setActiveTab] = useState<'picks' | 'backtest'>('picks');
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined);

  const preselection = useBoardPreselection();
  const history = useBoardPicks(selectedDate);
  const { data: dates = [] } = useBoardDates();
  const syncMutation = useSyncBoardPicks();

  const isHistory = !!selectedDate;
  const stage: 'pre' | 'final' = isHistory ? 'final' : (preselection.data?.stage ?? 'pre');
  const picks: BoardPick[] = isHistory
    ? (history.data ?? [])
    : (preselection.data?.picks ?? []);
  const targetDate = isHistory
    ? selectedDate
    : (preselection.data?.targetDate ?? '');
  const sourceDate = isHistory ? selectedDate : (preselection.data?.sourceDate ?? '');
  const isLoading = isHistory ? history.isLoading : preselection.isLoading;
  const isError = isHistory ? history.isError : preselection.isError;
  const refetch = isHistory ? history.refetch : preselection.refetch;
  const top = useMemo(() => picks.find((p) => p.isTop) ?? picks[0], [picks]);

  const handleCopy = async () => {
    if (!picks.length) {
      message.info('暂无可复制的股票');
      return;
    }
    const text = picks.map((p) => `${p.name}(${p.code})`).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      message.success(`已复制 ${picks.length} 只股票`);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      message.success(`已复制 ${picks.length} 只股票`);
    }
  };

  const handleSync = () => {
    syncMutation.mutate(undefined, {
      onSuccess: (result) => {
        if (result.stage === 'final') {
          setSelectedDate(result.targetDate);
          message.success(`已完成最终计算，共 ${result.picks.length} 只候选`);
        } else {
          setSelectedDate(undefined);
          message.success(
            `已更新预选，共 ${result.picks.length} 只；${result.targetDate} 09:30 后自动应用最终规则`,
          );
        }
      },
      onError: () => message.error('重新计算失败，请稍后重试'),
    });
  };

  const preColumns: ColumnType<BoardPick>[] = [
    {
      title: '序号',
      dataIndex: 'rank',
      key: 'rank',
      width: 60,
      align: 'center',
      render: (rank: number) => (
        <span style={{ color: COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>{rank}</span>
      ),
    },
    {
      title: '股票',
      key: 'stock',
      width: 150,
      fixed: 'left',
      render: (_: unknown, record: BoardPick) => (
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.textPrimary }}>{record.name}</div>
          <div style={{ fontSize: 11, color: COLORS.textMuted }}>{record.code}</div>
        </div>
      ),
    },
    {
      title: '板块',
      dataIndex: 'industry',
      key: 'industry',
      width: 110,
      render: (v?: string) =>
        v ? (
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
        ) : (
          <span style={{ color: COLORS.textMuted }}>—</span>
        ),
    },
    {
      title: '首板日',
      dataIndex: 'limitUpDate',
      key: 'limitUpDate',
      width: 110,
      render: (v?: string) => <span style={{ color: COLORS.textSecondary }}>{v ?? '—'}</span>,
    },
    {
      title: '首板日涨幅',
      dataIndex: 'changePct',
      key: 'changePct',
      width: 110,
      sorter: (a, b) => a.changePct - b.changePct,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? COLORS.rise : COLORS.fall, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
          {formatChangePct(v)}
        </span>
      ),
    },
    {
      title: '收盘价',
      dataIndex: 'close',
      key: 'close',
      width: 90,
      render: (v?: number) => (
        <span style={{ color: COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>
          {v !== undefined ? v.toFixed(2) : '—'}
        </span>
      ),
    },
    {
      title: '成交量',
      dataIndex: 'volume',
      key: 'volume',
      width: 100,
      render: (v?: number) => <span style={{ color: COLORS.textSecondary }}>{formatVolume(v)}</span>,
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      width: 320,
      render: (v?: string) => <span style={{ color: COLORS.textMuted, fontSize: 12 }}>{v ?? '—'}</span>,
    },
  ];

  const finalColumns: ColumnType<BoardPick>[] = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 68,
      align: 'center',
      render: (rank: number, record: BoardPick) =>
        record.isTop ? (
          <Tag color="red" style={{ margin: 0, fontSize: 11 }}>
            <TrophyOutlined /> 首选
          </Tag>
        ) : (
          <span style={{ color: COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>{rank}</span>
        ),
    },
    {
      title: '股票',
      key: 'stock',
      width: 150,
      fixed: 'left',
      render: (_: unknown, record: BoardPick) => (
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.textPrimary }}>{record.name}</div>
          <div style={{ fontSize: 11, color: COLORS.textMuted }}>{record.code}</div>
        </div>
      ),
    },
    {
      title: '开盘涨幅',
      dataIndex: 'openPct',
      key: 'openPct',
      width: 100,
      sorter: (a, b) => (a.openPct ?? 0) - (b.openPct ?? 0),
      defaultSortOrder: 'ascend',
      render: (v?: number) =>
        v === undefined ? (
          <span style={{ color: COLORS.textMuted }}>—</span>
        ) : (
          <span style={{ color: v >= 0 ? COLORS.rise : COLORS.fall, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
            {formatChangePct(v)}
          </span>
        ),
    },
    {
      title: '开盘价',
      dataIndex: 'price',
      key: 'price',
      width: 90,
      render: (v?: number) => (
        <span style={{ color: COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>
          {v !== undefined ? v.toFixed(2) : '—'}
        </span>
      ),
    },
    {
      title: '现价/涨幅',
      key: 'change',
      width: 110,
      sorter: (a, b) => a.changePct - b.changePct,
      render: (_: unknown, record: BoardPick) => (
        <div>
          <div style={{ color: COLORS.textPrimary, fontVariantNumeric: 'tabular-nums' }}>
            {record.close !== undefined ? record.close.toFixed(2) : '—'}
          </div>
          <div style={{ color: record.changePct >= 0 ? COLORS.rise : COLORS.fall, fontSize: 12 }}>
            {formatChangePct(record.changePct)}
          </div>
        </div>
      ),
    },
    {
      title: '昨收',
      dataIndex: 'prevClose',
      key: 'prevClose',
      width: 90,
      render: (v: number) => (
        <span style={{ color: COLORS.textSecondary, fontVariantNumeric: 'tabular-nums' }}>{v.toFixed(2)}</span>
      ),
    },
    {
      title: '成交量',
      dataIndex: 'volume',
      key: 'volume',
      width: 100,
      render: (v?: number) => <span style={{ color: COLORS.textSecondary }}>{formatVolume(v)}</span>,
    },
    {
      title: '板块',
      dataIndex: 'industry',
      key: 'industry',
      width: 100,
      render: (v?: string) =>
        v ? (
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
        ) : (
          <span style={{ color: COLORS.textMuted }}>—</span>
        ),
    },
    {
      title: '首板日',
      dataIndex: 'limitUpDate',
      key: 'limitUpDate',
      width: 105,
      render: (v?: string) => <span style={{ color: COLORS.textSecondary }}>{v ?? '—'}</span>,
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      width: 260,
      render: (v?: string) => <span style={{ color: COLORS.textMuted, fontSize: 12 }}>{v ?? '—'}</span>,
    },
  ];

  const dateOptions = [
    {
      value: '',
      label: (preselection.data?.stage ?? 'pre') === 'final' ? '当前（最终）' : '预选（下一交易日）',
    },
    ...dates.map((d) => ({ value: d, label: `${d}（最终）` })),
  ];
  if (isHistory && selectedDate && !dates.includes(selectedDate)) {
    dateOptions.push({ value: selectedDate, label: `${selectedDate}（最终）` });
  }

  return (
    <div>
      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as 'picks' | 'backtest')}
        items={[
          { key: 'picks', label: '选股' },
          { key: 'backtest', label: '回测' },
        ]}
        tabBarStyle={{ marginBottom: 16, borderBottom: '1px solid var(--c-border)' }}
      />
      {activeTab === 'picks' ? (
        <>
      <div style={{ marginBottom: isMobile ? 12 : 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: COLORS.textPrimary }}>打板</span>
          {stageBadge(stage)}
        </div>
        <div style={{ fontSize: 12, color: COLORS.textMuted, lineHeight: 1.7 }}>
          {stage === 'pre'
            ? `下一交易日 ${targetDate || '—'} 预选：基于 ${sourceDate || '—'} 首板，仅应用规则 ①-④；${targetDate || '次日'} 09:30 后自动应用开盘涨幅过滤与排序`
            : `最终选股 ${targetDate || '—'}：已应用规则 ①-⑥，按开盘涨幅升序排名，首选为策略买入标的`}
        </div>
        {picks.length > 0 && (
          <div style={{ fontSize: 12, color: COLORS.textMuted, marginTop: 6 }}>
            {stage === 'pre'
              ? `预选 ${picks.length} 只（待次日开盘确认）`
              : `最终 ${picks.length} 只${top ? ` · 首选 ${top.name}（${top.code}）` : ''}`}
          </div>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <Space size={8}>
          <Select
            size="small"
            value={selectedDate ?? ''}
            style={{ width: 190 }}
            options={dateOptions}
            onChange={(v) => setSelectedDate(v || undefined)}
            placeholder="选择交易日"
          />
          <span style={{ fontSize: 12, color: COLORS.textMuted }}>最终结果仅保留近 10 个交易日</span>
        </Space>
        <Space size={8}>
          <Button size="small" icon={<CopyOutlined />} onClick={handleCopy} style={{ fontSize: 12 }}>
            一键复制
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()} style={{ fontSize: 12 }}>
            刷新
          </Button>
          <Button
            size="small"
            icon={<SyncOutlined spin={syncMutation.isPending} />}
            loading={syncMutation.isPending}
            onClick={handleSync}
            style={{ borderColor: COLORS.chartBlue, color: COLORS.chartBlue, background: 'rgba(24,144,255,0.08)', fontSize: 12 }}
          >
            重新计算
          </Button>
        </Space>
      </div>

      {isLoading ? (
        <LoadingState height={300} tip="正在计算打板选股（首次需拉取全市场日线，请稍候）..." />
      ) : isError ? (
        <ErrorState message="打板选股加载失败" onRetry={refetch} />
      ) : picks.length === 0 ? (
        <EmptyState
          description={
            stage === 'pre'
              ? `暂无预选标的（基于 ${sourceDate || '最新交易日'} 首板，规则 ①-④）`
              : `${targetDate || selectedDate} 无符合条件的最终标的`
          }
          height={220}
        />
      ) : (
        <Table<BoardPick>
          columns={stage === 'pre' ? preColumns : finalColumns}
          dataSource={picks}
          rowKey="code"
          size="small"
          scroll={{ x: stage === 'pre' ? 940 : 1080 }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            showTotal: (total) => `共 ${total} 只`,
            style: { color: COLORS.textSecondary },
          }}
          style={{ background: 'transparent' }}
        />
      )}

      <div
        style={{
          marginTop: 24,
          padding: '12px 16px',
          background: COLORS.bgCard,
          borderRadius: 8,
          fontSize: 12,
          color: COLORS.textMuted,
          lineHeight: 1.8,
        }}
      >
        <strong style={{ color: COLORS.textSecondary }}>选股规则</strong>
        ：① 首板涨停（涨停日当天涨停、前一交易日未涨停，且首板日首次封板早于 14:10）；② 剔除一字板；③ 剔除首板日收盘偏离 MA20 &gt; 30%；
        ④ 剔除近 10 日涨停 ≥ 4 次；⑤ 次日开盘涨幅落在 [-10%, -4%)；⑥ 按开盘涨幅升序排名，第 1 名为策略首选。
        股票池为主板（600/601/603/605/000/001/002/003），已剔除科创板 688、创业板 300/301、北交所与 ST。
        <br />
        收盘后展示「下一交易日预选」（仅规则 ①-④）；次日 09:30 后自动应用规则 ⑤⑥ 得到最终结果并落库，
        也可随时点击「重新计算」立即触发。最终结果仅保留最近 10 个交易日。
      </div>
        </>
      ) : (
        <BoardBacktestView />
      )}
    </div>
  );
}
