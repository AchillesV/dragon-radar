import ReactECharts from 'echarts-for-react';
import { COLORS } from '../../constants/colors';
import { useFundFlow } from '../../hooks/useMarketData';
import { LoadingState } from '../common/StatusStates';
import type { FundFlowItem } from '../../types';

function buildOption(data: FundFlowItem[]) {
  const sorted = [...data].sort((a, b) => a.amount - b.amount);
  const names = sorted.map((d) => d.name);
  const amounts = sorted.map((d) => d.amount);

  return {
    backgroundColor: 'transparent',
    grid: { top: 10, right: 30, bottom: 10, left: 80 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'none' },
      backgroundColor: '#252836',
      borderColor: '#3d4255',
      textStyle: { color: COLORS.textPrimary, fontSize: 12 },
      formatter: (params: Array<{ name: string; value: number }>) => {
        const p = params[0];
        const item = data.find((d) => d.name === p.name);
        return `<div style="padding:4px 8px">
          <b>${p.name}</b><br/>
          净流入：<span style="color:${p.value >= 0 ? COLORS.rise : COLORS.fall}">
            ${p.value >= 0 ? '+' : ''}${p.value.toFixed(1)}亿
          </span><br/>
          涨跌幅：<span style="color:${(item?.changePct ?? 0) >= 0 ? COLORS.rise : COLORS.fall}">
            ${(item?.changePct ?? 0) >= 0 ? '+' : ''}${(item?.changePct ?? 0).toFixed(2)}%
          </span>
        </div>`;
      },
    },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#3d4255' } },
      splitLine: { lineStyle: { color: '#252836', type: 'dashed' } },
      axisLabel: {
        color: COLORS.textMuted,
        fontSize: 11,
        formatter: (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(0)}亿`,
      },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: COLORS.textSecondary, fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: amounts.map((v) => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? COLORS.chartRed : COLORS.chartGreen,
            borderRadius: v >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3],
          },
          label: {
            show: true,
            position: v >= 0 ? 'right' : 'left',
            formatter: ({ value }: { value: number }) =>
              `${value >= 0 ? '+' : ''}${value.toFixed(1)}亿`,
            color: v >= 0 ? COLORS.rise : COLORS.fall,
            fontSize: 11,
          },
        })),
        barMaxWidth: 20,
      },
    ],
  };
}

export default function FundFlowChart() {
  const { data, isLoading } = useFundFlow();

  return (
    <div style={{ background: COLORS.bgCard, borderRadius: 8, padding: '16px 16px 8px' }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.textPrimary, marginBottom: 8 }}>
        主力资金净流入（板块）
      </div>
      {isLoading ? (
        <LoadingState height={250} />
      ) : data ? (
        <ReactECharts option={buildOption(data)} style={{ height: 250 }} />
      ) : null}
    </div>
  );
}
