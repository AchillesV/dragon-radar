import ReactECharts from 'echarts-for-react';
import { COLORS } from '../../constants/colors';
import { useAmountHistory } from '../../hooks/useMarketData';
import { useTheme } from '../../hooks/useTheme';
import { LoadingState } from '../common/StatusStates';
import type { RawColors } from '../../constants/colors';

function buildOption(
  dates: string[],
  amounts: number[],
  ma5: (number | null)[],
  c: RawColors,
) {
  const lastIndex = amounts.length - 1;
  const barColors = amounts.map((_, i) => (i === lastIndex ? c.rise : c.textMuted));

  return {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 20, bottom: 40, left: 60 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: c.bgHover,
      borderColor: c.borderLight,
      textStyle: { color: c.textPrimary, fontSize: 12 },
      formatter: (params: Array<{ name: string; value: number; seriesName: string }>) => {
        const bar = params.find((p) => p.seriesName === '成交额');
        const ma = params.find((p) => p.seriesName === '5日均线');
        if (!bar) return '';
        const barVal = bar.value;
        const maVal = ma?.value;
        let deviation = '';
        if (maVal && maVal > 0) {
          const pct = (((barVal - maVal) / maVal) * 100).toFixed(1);
          deviation = `<br/>较5日均值 <span style="color:${Number(pct) >= 0 ? c.rise : c.fall}">${Number(pct) >= 0 ? '+' : ''}${pct}%</span>`;
        }
        return `<div style="padding:4px 8px">
          <div style="color:${c.textSecondary};margin-bottom:4px">${bar.name}</div>
          <div>成交额：<b style="color:${c.textPrimary}">${barVal.toFixed(2)}万亿</b></div>
          ${maVal ? `<div>5日均值：<b style="color:${c.chartGold}">${maVal.toFixed(2)}万亿</b></div>` : ''}
          ${deviation}
        </div>`;
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: c.borderLight } },
      axisTick: { show: false },
      axisLabel: { color: c.textMuted, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '万亿',
      nameTextStyle: { color: c.textMuted, fontSize: 11 },
      min: (value: { min: number }) => Math.floor(value.min * 10) / 10 - 0.1,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      axisLabel: { color: c.textMuted, fontSize: 11, formatter: (v: number) => v.toFixed(1) },
    },
    series: [
      {
        name: '成交额',
        type: 'bar',
        data: amounts,
        barMaxWidth: 30,
        itemStyle: {
          color: (params: { dataIndex: number }) => barColors[params.dataIndex],
          borderRadius: [2, 2, 0, 0],
        },
        emphasis: { itemStyle: { color: c.chartRed } },
      },
      {
        name: '5日均线',
        type: 'line',
        data: ma5,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: c.chartGold, width: 2, type: 'dashed' },
        connectNulls: true,
      },
    ],
  };
}

export default function AmountChart() {
  const { data, isLoading } = useAmountHistory();
  const { rawColors } = useTheme();

  if (isLoading) return <LoadingState height={300} />;
  if (!data) return null;

  const dates = data.map((d) => d.date);
  const amounts = data.map((d) => d.amount);
  const ma5: (number | null)[] = amounts.map((_, i) => {
    if (i < 4) return null;
    const sum = amounts.slice(i - 4, i + 1).reduce((a, b) => a + b, 0);
    return Math.round((sum / 5) * 100) / 100;
  });

  return (
    <div style={{ background: COLORS.bgCard, borderRadius: 8, padding: '16px 16px 8px' }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.textPrimary, marginBottom: 8 }}>
        近20日成交额
      </div>
      <ReactECharts option={buildOption(dates, amounts, ma5, rawColors)} style={{ height: 270 }} />
    </div>
  );
}
