import { useState } from 'react';
import { Tabs } from 'antd';
import TrendScreening from '../components/trend/TrendScreening';
import TrendAnalysisView from '../components/trend/TrendAnalysisView';

/**
 * 「趋势」页面 —— 内含两个 Tab：
 *   - 股票筛选：原有「放量启动 + 持续放量 + 横盘」候选池
 *   - 分析：V2 Phase 1，候选池 → 板块聚合 → 板块热度/量能趋势/扩散度
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
