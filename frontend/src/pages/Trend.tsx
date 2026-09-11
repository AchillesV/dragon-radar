import { useState } from 'react';
import { Tabs } from 'antd';
import TrendScreening from '../components/trend/TrendScreening';
import TrendAnalysisView from '../components/trend/TrendAnalysisView';
import TrendBacktestView from '../components/trend/TrendBacktestView';

/**
 * 「趋势」页面 —— 内含三个 Tab：
 *   - 股票筛选：原有「放量启动 + 持续放量 + 横盘」候选池
 *   - 分析：V2 Phase 1~4，候选池 → 板块 → 资金 → 共振 → 核心股 → 交易阶段 → 买点
 *   - 回测：V2 Phase 5，T+1/T+3/T+5/T+10 前向收益回测
 */
export default function Trend() {
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined);

  const items = [
    {
      key: 'screening',
      label: '股票筛选',
      children: <TrendScreening selectedDate={selectedDate} onDateChange={setSelectedDate} />,
    },
    {
      key: 'analysis',
      label: '分析',
      children: <TrendAnalysisView selectedDate={selectedDate} onDateChange={setSelectedDate} />,
    },
    {
      key: 'backtest',
      label: '回测',
      children: <TrendBacktestView />,
    },
  ];

  return (
    <div>
      <Tabs
        defaultActiveKey="screening"
        items={items}
        destroyInactiveTabPane
        tabBarStyle={{ marginBottom: 16, borderBottom: '1px solid var(--c-border)' }}
      />
    </div>
  );
}
