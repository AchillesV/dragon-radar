import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Tabs } from 'antd';
import { COLORS } from '../../constants/colors';
import { useIndustrySectors, useConceptSectors } from '../../hooks/useMarketData';
import { useTheme } from '../../hooks/useTheme';
import { LoadingState } from '../common/StatusStates';
import type { SectorRank } from '../../types';
import type { RawColors } from '../../constants/colors';

function buildOption(sectors: SectorRank[], c: RawColors) {
  const sorted = [...sectors].sort((a, b) => a.changePct - b.changePct);
  const names = sorted.map((s) => s.name);
  const values = sorted.map((s) => s.changePct);
  const leadStocks = sorted.map((s) => s.leadStock ?? '');

  const colors = values.map((v) => {
    if (v >= 3) return c.limitUp;
    if (v > 0) return c.rise;
    return c.fall;
  });

  return {
    backgroundColor: 'transparent',
    grid: { top: 10, right: 120, bottom: 10, left: 80 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'none' },
      backgroundColor: c.bgHover,
      borderColor: c.borderLight,
      textStyle: { color: c.textPrimary, fontSize: 12 },
      formatter: (params: Array<{ name: string; value: number }>) => {
        const p = params[0];
        const sector = sorted.find((s) => s.name === p.name);
        return `<div style="padding:4px 8px">
          <b style="color:${c.textPrimary}">${p.name}</b><br/>
          涨幅：<span style="color:${p.value >= 0 ? c.rise : c.fall}">${p.value >= 0 ? '+' : ''}${p.value.toFixed(2)}%</span><br/>
          领涨：${sector?.leadStock ?? '-'} ${sector?.leadStockChangePct !== undefined ? `(${sector.leadStockChangePct >= 0 ? '+' : ''}${sector.leadStockChangePct.toFixed(2)}%)` : ''}
        </div>`;
      },
    },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: c.borderLight } },
      splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      axisLabel: {
        color: c.textMuted,
        fontSize: 11,
        formatter: (v: number) => `${v.toFixed(1)}%`,
      },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: c.textSecondary, fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i], borderRadius: v >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3] },
          label: {
            show: true,
            position: v >= 0 ? 'right' : 'left',
            formatter: () => leadStocks[i],
            color: c.textMuted,
            fontSize: 11,
          },
        })),
        barMaxWidth: 20,
      },
    ],
  };
}

export default function SectorRankChart() {
  const [activeTab, setActiveTab] = useState<'industry' | 'concept'>('industry');
  const { data: industryData, isLoading: industryLoading } = useIndustrySectors();
  const { data: conceptData, isLoading: conceptLoading } = useConceptSectors();
  const { rawColors } = useTheme();

  const isLoading = activeTab === 'industry' ? industryLoading : conceptLoading;
  const data = activeTab === 'industry' ? industryData : conceptData;

  return (
    <div style={{ background: COLORS.bgCard, borderRadius: 8, padding: '8px 16px 8px' }}>
      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as 'industry' | 'concept')}
        size="small"
        items={[
          { key: 'industry', label: '行业板块' },
          { key: 'concept', label: '概念板块' },
        ]}
        tabBarStyle={{ color: COLORS.textSecondary, marginBottom: 4 }}
      />
      {isLoading ? (
        <LoadingState height={320} />
      ) : data ? (
        <ReactECharts key={activeTab} option={buildOption(data, rawColors)} style={{ height: 320 }} />
      ) : null}
    </div>
  );
}
