import { Row, Col } from 'antd';
import StatCard from '../components/dashboard/StatCard';
import AmountChart from '../components/dashboard/AmountChart';
import SectorRankChart from '../components/dashboard/SectorRankChart';
import FundFlowChart from '../components/dashboard/FundFlowChart';
import LianbanTier from '../components/dashboard/LianbanTier';
import { useMarketOverview } from '../hooks/useMarketData';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';

export default function Dashboard() {
  const { data: overview } = useMarketOverview();
  const isMobile = useIsMobile();

  return (
    <div>
      {/* Stat cards — 2-col grid on mobile, flex row on desktop */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(5, 1fr)',
          gap: isMobile ? 8 : 12,
          marginBottom: isMobile ? 12 : 16,
        }}
      >
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
        {/* 成交额跨2列，在移动端占整行 */}
        <div style={{ gridColumn: isMobile ? '1 / -1' : 'auto' }}>
          <StatCard
            title="今日成交额"
            value={overview?.totalAmount?.toFixed(2) ?? '--'}
            suffix="万亿"
            subtitle={`最高连板：${overview?.maxLianban?.name ?? '--'} ${overview?.maxLianban?.count ?? '--'}板`}
            color="gold"
          />
        </div>
      </div>

      {/* Amount chart */}
      <div style={{ marginBottom: isMobile ? 12 : 16 }}>
        <AmountChart />
      </div>

      {/* Sector charts — stacked on mobile */}
      <Row gutter={isMobile ? [0, 12] : 16} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={24} md={12}>
          <SectorRankChart />
        </Col>
        <Col xs={24} md={12}>
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
