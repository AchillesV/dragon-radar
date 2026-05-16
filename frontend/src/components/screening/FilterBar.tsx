import { useState } from 'react';
import { Select, Slider, Button, Space, InputNumber, Row, Col } from 'antd';
import { FilterOutlined, RedoOutlined } from '@ant-design/icons';
import { COLORS } from '../../constants/colors';

export interface FilterValues {
  market?: string[];
  industry?: string[];
  changePctMin?: number;
  changePctMax?: number;
  amountMin?: number;
  turnoverMin?: number;
  marketCapMax?: number;
  lianbanMin?: number;
  [key: string]: unknown;
}

interface FilterBarProps {
  onChange?: (values: FilterValues) => void;
}

const industries = [
  '电力设备', '通信', '半导体', '计算机', '国防军工', '化工',
  '机械设备', '汽车', '银行', '建筑装饰', '电子', '食品饮料',
  '医药生物', '有色金属', '钢铁',
];

export default function FilterBar({ onChange }: FilterBarProps) {
  const [filters, setFilters] = useState<FilterValues>({});
  const [expanded, setExpanded] = useState(false);

  const update = (key: keyof FilterValues, value: unknown) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleApply = () => {
    onChange?.(filters);
  };

  const handleReset = () => {
    setFilters({});
    onChange?.({});
  };

  const selectStyle = {
    background: '#252836',
  };

  return (
    <div
      style={{
        background: COLORS.bgCard,
        borderRadius: 8,
        padding: '12px 16px',
        marginBottom: 16,
        border: '1px solid #252836',
      }}
    >
      <Row gutter={[12, 12]} align="middle">
        {/* Market */}
        <Col>
          <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>市场</div>
          <Select
            mode="multiple"
            placeholder="全部"
            style={{ width: 160, ...selectStyle }}
            size="small"
            value={filters.market}
            onChange={(v) => update('market', v)}
            options={[
              { label: '沪市(SH)', value: 'SH' },
              { label: '深市(SZ)', value: 'SZ' },
              { label: '北交所(BJ)', value: 'BJ' },
            ]}
            maxTagCount="responsive"
          />
        </Col>

        {/* Industry */}
        <Col>
          <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>行业</div>
          <Select
            mode="multiple"
            placeholder="全部行业"
            style={{ width: 200 }}
            size="small"
            value={filters.industry}
            onChange={(v) => update('industry', v)}
            options={industries.map((i) => ({ label: i, value: i }))}
            maxTagCount="responsive"
          />
        </Col>

        {/* Change pct range */}
        <Col>
          <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>涨幅范围(%)</div>
          <Space size={4}>
            <InputNumber
              size="small"
              style={{ width: 64, background: '#252836', borderColor: '#3d4255', color: COLORS.textPrimary }}
              placeholder="-10"
              value={filters.changePctMin}
              onChange={(v) => update('changePctMin', v)}
            />
            <span style={{ color: COLORS.textMuted }}>~</span>
            <InputNumber
              size="small"
              style={{ width: 64, background: '#252836', borderColor: '#3d4255', color: COLORS.textPrimary }}
              placeholder="+10"
              value={filters.changePctMax}
              onChange={(v) => update('changePctMax', v)}
            />
          </Space>
        </Col>

        {/* Amount min */}
        <Col>
          <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>最小成交额(亿)</div>
          <InputNumber
            size="small"
            style={{ width: 90, background: '#252836', borderColor: '#3d4255', color: COLORS.textPrimary }}
            placeholder="0"
            min={0}
            value={filters.amountMin}
            onChange={(v) => update('amountMin', v ?? undefined)}
          />
        </Col>

        {expanded && (
          <>
            {/* Turnover */}
            <Col>
              <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>最小换手率(%)</div>
              <div style={{ width: 120 }}>
                <Slider
                  min={0}
                  max={30}
                  value={filters.turnoverMin ?? 0}
                  onChange={(v) => update('turnoverMin', v)}
                  tooltip={{ formatter: (v) => `${v}%` }}
                  trackStyle={{ background: COLORS.chartRed }}
                  handleStyle={{ borderColor: COLORS.chartRed }}
                />
              </div>
            </Col>

            {/* Lianban min */}
            <Col>
              <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>最小连板数</div>
              <InputNumber
                size="small"
                style={{ width: 80, background: '#252836', borderColor: '#3d4255', color: COLORS.textPrimary }}
                min={0}
                max={20}
                placeholder="0"
                value={filters.lianbanMin}
                onChange={(v) => update('lianbanMin', v ?? undefined)}
              />
            </Col>
          </>
        )}

        {/* Actions */}
        <Col style={{ marginLeft: 'auto' }}>
          <Space>
            <Button
              size="small"
              type="link"
              style={{ color: COLORS.textMuted, fontSize: 12 }}
              onClick={() => setExpanded(!expanded)}
              icon={<FilterOutlined />}
            >
              {expanded ? '收起' : '更多筛选'}
            </Button>
            <Button
              size="small"
              icon={<RedoOutlined />}
              onClick={handleReset}
              style={{ borderColor: '#3d4255', color: COLORS.textMuted, background: 'transparent' }}
            >
              重置
            </Button>
            <Button
              size="small"
              type="primary"
              onClick={handleApply}
              style={{ background: COLORS.chartRed, borderColor: COLORS.chartRed }}
            >
              应用筛选
            </Button>
          </Space>
        </Col>
      </Row>
    </div>
  );
}
