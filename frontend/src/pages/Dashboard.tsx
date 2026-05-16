import { Row, Col } from 'antd';
import StatCard from '../components/dashboard/StatCard';
import AmountChart from '../components/dashboard/AmountChart';
import SectorRankChart from '../components/dashboard/SectorRankChart';
import FundFlowChart from '../components/dashboard/FundFlowChart';
import LianbanTier from '../components/dashboard/LianbanTier';
import { useMarketOverview } from '../hooks/useMarketData';
import { COLORS } from '../constants/colors';

export default function Dashboard() {
  const { data: overview } = useMarketOverview();

  return (
    <div>
      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <StatCard
          title="今日上涨"
          value={overview?.riseCount?.toLocaleString() ?? '--'}
          subtitle="家"
          delta={overview?.riseCountDelta}
          deltaLabel="较昨日"
          color="red"
        />
        <StatCard
          title="今日下跌"
          value={overview?.fallCount?.toLocaleString() ?? '--'}
          subtitle="家"
          color="green"
        />
        <StatCard
          title="涨停家数"
          value={overview?.limitUpCount ?? '--'}
          subtitle="家"
          delta={overview?.limitUpCountDelta}
          deltaLabel="家"
          color="red"
        />
        <StatCard
          title="跌停家数"
          value={overview?.limitDownCount ?? '--'}
          subtitle="家"
          color="green"
        />
        <StatCard
          title="今日成交额"
          value={overview?.totalAmount?.toFixed(2) ?? '--'}
          suffix="万亿"
          subtitle={`最高连板：${overview?.maxLianban?.name ?? '--'} ${overview?.maxLianban?.count ?? '--'}板`}
          color="gold"
        />
      </div>

      {/* Amount chart */}
      <div style={{ marginBottom: 16 }}>
        <AmountChart />
      </div>

      {/* Sector charts */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <SectorRankChart />
        </Col>
        <Col span={12}>
          <div style={{ background: COLORS.bgCard, borderRadius: 8, padding: '8px 16px' }}>
            <FundFlowChart />
          </div>
        </Col>
      </Row>

      {/* Lianban tier */}
      <LianbanTier />
    </div>
  );
}
