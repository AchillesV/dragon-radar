import { useMemo, useState } from 'react';
import { Table, Select, Button, Space, message, Tag } from 'antd';
import { SyncOutlined, TrophyOutlined } from '@ant-design/icons';
import type { ColumnType } from 'antd/es/table';
import { useBoardPicks, useBoardDates, useSyncBoardPicks } from '../hooks/useBoardData';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';
import { formatChangePct } from '../utils/format';
import { LoadingState, EmptyState, ErrorState } from '../components/common/StatusStates';
import type { BoardPick } from '../types';

function formatVolume(v?: number): string {
  if (v === undefined || v === null) return '—';
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万手`;
  return `${v.toFixed(0)}手`;
}

export default function Board() {
  const isMobile = useIsMobile();
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined);
  const { data: dates = [] } = useBoardDates();
  const { data, isLoading, isError, refetch } = useBoardPicks(selectedDate);
  const syncMutation = useSyncBoardPicks();

  const picks = data ?? [];
  const top = useMemo(() => picks.find((p) => p.isTop) ?? picks[0], [picks]);

  const handleSync = () => {
    syncMutation.mutate(undefined, {
      onSuccess: (rows) => {
        setSelectedDate(undefined);
        message.success(`已重新计算，共 ${rows.length} 只候选`);
      },
      onError: () => message.error('重新计算失败，请稍后重试'),
    });
  };

  const columns: ColumnType<BoardPick>[] = [
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
      sorter: (a, b) => a.openPct - b.openPct,
      defaultSortOrder: 'ascend',
      render: (v: number) => (
        <span
          style={{
            color: v >= 0 ? COLORS.rise : COLORS.fall,
            fontWeight: 600,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
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
    { value: '', label: '最新交易日' },
    ...dates.map((d) => ({ value: d, label: d })),
  ];

  return (
    <div>
      <div style={{ marginBottom: isMobile ? 12 : 20 }}>
        <div style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>
          打板
        </div>
        <div style={{ fontSize: 12, color: COLORS.textMuted, lineHeight: 1.7 }}>
          昨日首板 + 今日低开区间（开盘涨幅 -10% ~ -4%），按开盘涨幅升序排名，首选为策略买入标的
        </div>
        {data && data.length > 0 && (
          <div style={{ fontSize: 12, color: COLORS.textMuted, marginTop: 6 }}>
            选股交易日 {data[0].date} · 候选 {data.length} 只
            {top ? ` · 首选 ${top.name}（${top.code}）` : ''}
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
            style={{ width: 150 }}
            options={dateOptions}
            onChange={(v) => setSelectedDate(v || undefined)}
            placeholder="选择交易日"
          />
          <span style={{ fontSize: 12, color: COLORS.textMuted }}>仅保留近 10 个交易日</span>
        </Space>
        <Space size={8}>
          <Button size="small" onClick={() => refetch()} style={{ fontSize: 12 }}>
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
            selectedDate
              ? `${selectedDate} 无符合条件的打板标的`
              : '今日暂无符合「昨日首板 + 今日低开 -10%~-4%」的标的'
          }
          height={220}
        />
      ) : (
        <Table<BoardPick>
          columns={columns}
          dataSource={picks}
          rowKey="code"
          size="small"
          scroll={{ x: 1080 }}
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
        ：① 昨日（T-1）首板涨停且前一日未涨停；② 剔除昨日一字板；③ 剔除 T-1 收盘偏离 MA20 &gt; 30%；
        ④ 剔除近 10 日涨停 ≥ 4 次；⑤ 今日开盘涨幅落在 [-10%, -4%)；⑥ 按开盘涨幅升序排名，第 1 名为策略首选。
        股票池为主板（600/601/603/605/000/001/002/003），已剔除科创板 688、创业板 300/301、北交所与 ST。
        结果每日落库，仅保留最近 10 个交易日。
      </div>
    </div>
  );
}
