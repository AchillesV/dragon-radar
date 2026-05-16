import { useState } from 'react';
import { Button, Space } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import AnomalyCardComponent from '../components/anomaly/AnomalyCard';
import { useAnomalyCards } from '../hooks/useAnomalyData';
import { COLORS } from '../constants/colors';
import { LoadingState } from '../components/common/StatusStates';

export default function AnomalyMonitor() {
  const { data: cards, isLoading } = useAnomalyCards();
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);
  const [lastScan, setLastScan] = useState(new Date().toLocaleTimeString('zh-CN'));

  const handleRefresh = async () => {
    setRefreshing(true);
    await new Promise((r) => setTimeout(r, 2000));
    await queryClient.invalidateQueries({ queryKey: ['anomaly', 'cards'] });
    setLastScan(new Date().toLocaleTimeString('zh-CN'));
    setRefreshing(false);
  };

  if (isLoading) return <LoadingState height={400} tip="扫描异动数据中..." />;

  return (
    <div>
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
        }}
      >
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>
            异动监控
          </div>
          <div style={{ fontSize: 13, color: COLORS.textMuted }}>
            最后扫描：{lastScan} · 共 {cards?.length ?? 0} 种异动类型
          </div>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined spin={refreshing} />}
            onClick={handleRefresh}
            loading={refreshing}
            style={{
              borderColor: COLORS.chartRed,
              color: COLORS.chartRed,
              background: 'rgba(255,77,79,0.08)',
            }}
          >
            {refreshing ? '扫描中...' : '手动刷新'}
          </Button>
        </Space>
      </div>

      {/* 4-col grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 12,
        }}
      >
        {(cards ?? []).map((card) => (
          <AnomalyCardComponent key={card.id} card={card} loading={refreshing} />
        ))}
      </div>

      {/* Tips */}
      <div
        style={{
          marginTop: 24,
          padding: '12px 16px',
          background: COLORS.bgCard,
          borderRadius: 8,
          fontSize: 12,
          color: COLORS.textMuted,
          lineHeight: 1.7,
        }}
      >
        💡 <strong style={{ color: COLORS.textSecondary }}>使用提示</strong>：
        点击异动卡片可查看具体异动股票列表。系统每30秒自动更新一次，也可手动刷新获取最新数据。
        红色数字表示该类型的异动股票数量，点击后可查看详细分析并生成个股报告。
      </div>
    </div>
  );
}
