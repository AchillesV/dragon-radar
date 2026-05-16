import { useParams, useNavigate } from 'react-router-dom';
import { Breadcrumb, Button } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined } from '@ant-design/icons';
import type { AnomalyType } from '../types';
import { useAnomalyCards } from '../hooks/useAnomalyData';
import { useAnomalyStocks } from '../hooks/useAnomalyData';
import StockTable from '../components/screening/StockTable';
import { COLORS } from '../constants/colors';
import { LoadingState } from '../components/common/StatusStates';

export default function AnomalyDetail() {
  const { type } = useParams<{ type: string }>();
  const navigate = useNavigate();
  const { data: cards } = useAnomalyCards();
  const { data: stocks, isLoading } = useAnomalyStocks(type as AnomalyType);

  const card = cards?.find((c) => c.id === type);
  const typeName = card?.title ?? type ?? '异动';

  const handleExportCSV = () => {
    if (!stocks) return;
    const headers = ['代码', '名称', '价格', '涨跌幅', '成交额(亿)', '换手率'];
    const rows = stocks.map((s) => [
      s.code,
      s.name,
      s.price.toFixed(2),
      `${s.changePct >= 0 ? '+' : ''}${s.changePct.toFixed(2)}%`,
      (s.amount / 10000).toFixed(2),
      `${s.turnoverRate.toFixed(2)}%`,
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `异动-${typeName}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      {/* Breadcrumb */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/anomaly')}
            style={{ color: COLORS.textSecondary, padding: '4px 8px' }}
          />
          <Breadcrumb
            items={[
              {
                title: (
                  <span
                    style={{ color: COLORS.textSecondary, cursor: 'pointer' }}
                    onClick={() => navigate('/anomaly')}
                  >
                    异动监控
                  </span>
                ),
              },
              {
                title: (
                  <span style={{ color: COLORS.textPrimary, fontWeight: 600 }}>
                    {card?.icon} {typeName}
                  </span>
                ),
              },
            ]}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {!isLoading && (
            <span style={{ fontSize: 13, color: COLORS.textSecondary }}>
              共 <span style={{ color: COLORS.textPrimary, fontWeight: 600 }}>{stocks?.length ?? 0}</span> 只
            </span>
          )}
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={handleExportCSV}
            style={{ borderColor: '#3d4255', color: COLORS.textMuted, background: 'transparent' }}
          >
            导出CSV
          </Button>
        </div>
      </div>

      {/* Description */}
      {card && (
        <div
          style={{
            background: COLORS.bgCard,
            borderRadius: 8,
            padding: '12px 16px',
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            border: '1px solid #252836',
          }}
        >
          <span style={{ fontSize: 28 }}>{card.icon}</span>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: COLORS.textPrimary, marginBottom: 2 }}>
              {card.title}
            </div>
            <div style={{ fontSize: 13, color: COLORS.textSecondary }}>{card.description}</div>
          </div>
          <div
            style={{
              marginLeft: 'auto',
              fontSize: 32,
              fontWeight: 700,
              color: COLORS.chartRed,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {card.count}
          </div>
        </div>
      )}

      {/* Stock table */}
      {isLoading ? (
        <LoadingState height={300} tip="加载异动股票..." />
      ) : (
        <StockTable
          stocks={stocks ?? []}
          mode="anomaly"
          anomalyType={type as AnomalyType}
          showOperationGuide={true}
        />
      )}
    </div>
  );
}
