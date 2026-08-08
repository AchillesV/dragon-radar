import ReactECharts from 'echarts-for-react';
import { COLORS } from '../../constants/colors';
import { LoadingState } from '../common/StatusStates';
import type { MainlineSector } from '../../types';
import type { RawColors } from '../../constants/colors';

function formatYi(v: number): string {
  const yi = v / 1e8;
  return `${yi >= 0 ? '+' : ''}${yi.toFixed(2)}亿`;
}

function buildOption(data: MainlineSector[], c: RawColors) {
  const sorted = [...data].sort((a, b) => a.netInflow - b.netInflow);
  const names = sorted.map((d) => d.name);
  const amounts = sorted.map((d) => d.netInflow);

  return {
    backgroundColor: 'transparent',
    grid: { top: 10, right: 40, bottom: 10, left: 150 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'none' },
      backgroundColor: c.bgHover,
      borderColor: c.borderLight,
      textStyle: { color: c.textPrimary, fontSize: 12 },
      formatter: (params: Array<{ name: string; value: number }>) => {
        const p = params[0];
        const item = sorted.find((d) => d.name === p.name);
        const dataIssue = item && item.matchedCount < item.stockCount;
        return `<div style="padding:4px 8px">
          <b>${p.name}</b><br/>
          主力净流入：<span style="color:${p.value >= 0 ? c.rise : c.fall}">${formatYi(p.value)}</span><br/>
          分类股票：${item?.stockCount ?? 0} 只${dataIssue ? `（仅 ${item?.matchedCount} 只取到实时资金流数据）` : ''}
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
        formatter: (v: number) => formatYi(v),
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
        data: amounts.map((v) => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? c.chartRed : c.chartGreen,
            borderRadius: v >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3],
          },
          label: {
            show: true,
            position: v >= 0 ? 'right' : 'left',
            formatter: ({ value }: { value: number }) => formatYi(value as number),
            color: v >= 0 ? c.rise : c.fall,
            fontSize: 11,
          },
        })),
        barMaxWidth: 18,
      },
    ],
  };
}

interface Props {
  data: MainlineSector[];
  loading?: boolean;
  rawColors: RawColors;
}

export default function MainlineFlowChart({ data, loading, rawColors }: Props) {
  const totalMatched = data.reduce((sum, d) => sum + d.matchedCount, 0);
  const totalStocks = data.reduce((sum, d) => sum + d.stockCount, 0);
  const dataStale = totalStocks > 0 && totalMatched === 0;

  return (
    <div style={{ background: COLORS.bgCard, borderRadius: 8, padding: '16px 16px 8px' }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.textPrimary, marginBottom: 8 }}>
        科技子板块主力资金净流入
      </div>
      {loading ? (
        <LoadingState height={480} />
      ) : data.length === 0 ? (
        <div style={{ height: 480, display: 'flex', alignItems: 'center', justifyContent: 'center', color: COLORS.textMuted }}>
          暂无数据
        </div>
      ) : (
        <>
          {dataStale && (
            <div style={{ fontSize: 12, color: COLORS.chartGold, marginBottom: 8 }}>
              ⚠️ 资金流数据源暂时不可用，以下数值可能为 0，请稍后重试
            </div>
          )}
          <ReactECharts option={buildOption(data, rawColors)} style={{ height: 480 }} />
        </>
      )}
    </div>
  );
}
