import { Modal, Tag, Rate, Divider, Space } from 'antd';
import { WarningOutlined, BulbOutlined, EyeOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import type { BulkAnalysisResult } from '../../types';
import { COLORS } from '../../constants/colors';

interface BulkAnalysisModalProps {
  result: BulkAnalysisResult | null;
  open: boolean;
  onClose: () => void;
  loading?: boolean;
}

const sentimentConfig = {
  strong: { label: '强势市场', color: COLORS.chartRed, bg: 'rgba(255,77,79,0.12)' },
  normal: { label: '中性市场', color: COLORS.chartGold, bg: 'rgba(250,173,20,0.12)' },
  weak: { label: '弱势市场', color: COLORS.chartGreen, bg: 'rgba(82,196,26,0.12)' },
};

export default function BulkAnalysisModal({ result, open, onClose, loading }: BulkAnalysisModalProps) {
  if (!result && !loading) return null;

  const sentiment = result ? sentimentConfig[result.marketSentiment] : null;

  return (
    <Modal
      title={
        <span style={{ fontSize: 16, fontWeight: 700, color: COLORS.textPrimary }}>
          整体市场分析报告
        </span>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={900}
      loading={loading}
      styles={{
        content: { background: COLORS.bgCard },
        header: { background: COLORS.bgCard, borderBottom: `1px solid #252836` },
        body: { maxHeight: '80vh', overflow: 'auto', padding: '20px 24px' },
      }}
    >
      {result && (
        <div>
          {/* Header stats */}
          <div
            style={{
              display: 'flex',
              gap: 16,
              alignItems: 'center',
              marginBottom: 20,
              padding: '12px 16px',
              background: '#252836',
              borderRadius: 8,
            }}
          >
            {sentiment && (
              <div
                style={{
                  background: sentiment.bg,
                  border: `1px solid ${sentiment.color}`,
                  borderRadius: 6,
                  padding: '6px 16px',
                  color: sentiment.color,
                  fontWeight: 700,
                  fontSize: 14,
                }}
              >
                {sentiment.label}
              </div>
            )}
            <div style={{ color: COLORS.textSecondary, fontSize: 13 }}>
              候选股票：
              <span style={{ color: COLORS.textPrimary, fontWeight: 600 }}>
                {result.totalCandidates}
              </span>{' '}
              只
            </div>
            <div style={{ marginLeft: 'auto', color: COLORS.textMuted, fontSize: 12 }}>
              {result.date}
            </div>
          </div>

          {/* Main themes */}
          <div style={{ marginBottom: 20 }}>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.textPrimary,
                marginBottom: 10,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <BulbOutlined style={{ color: COLORS.chartGold }} />
              今日主线题材
            </div>
            <Space wrap>
              {result.mainTheme.map((theme, i) => (
                <Tag
                  key={theme}
                  color={i === 0 ? 'red' : i === 1 ? 'orange' : 'blue'}
                  style={{ fontSize: 13, padding: '3px 12px' }}
                >
                  {i === 0 ? '🔥 ' : ''}{theme}
                </Tag>
              ))}
            </Space>
          </div>

          <Divider style={{ borderColor: '#252836', margin: '16px 0' }} />

          {/* Sector recommendations */}
          <div style={{ marginBottom: 20 }}>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.textPrimary,
                marginBottom: 12,
              }}
            >
              板块推荐
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {result.sectorRecommendation.map((rec, i) => (
                <div
                  key={rec.sector}
                  style={{
                    background: '#252836',
                    borderRadius: 8,
                    padding: '12px 16px',
                    border: i === 0 ? `1px solid rgba(255,77,79,0.3)` : `1px solid #3d4255`,
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: 6,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span
                        style={{
                          fontSize: 14,
                          fontWeight: 700,
                          color: i === 0 ? COLORS.chartRed : COLORS.textPrimary,
                        }}
                      >
                        {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`}{'  '}
                        {rec.sector}
                      </span>
                      <Rate
                        disabled
                        defaultValue={rec.stars}
                        style={{ fontSize: 12, color: COLORS.chartGold }}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {rec.keyStocks.map((stock) => (
                        <Tag key={stock} style={{ fontSize: 11, background: '#1a1d29', borderColor: '#3d4255' }}>
                          {stock}
                        </Tag>
                      ))}
                    </div>
                  </div>
                  <div style={{ fontSize: 12, color: COLORS.textSecondary, lineHeight: 1.6 }}>
                    {rec.reason}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Divider style={{ borderColor: '#252836', margin: '16px 0' }} />

          {/* AI Summary */}
          <div style={{ marginBottom: 20 }}>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.textPrimary,
                marginBottom: 10,
              }}
            >
              AI复盘分析
            </div>
            <div
              style={{
                background: '#252836',
                borderRadius: 8,
                padding: '12px 16px',
                fontSize: 13,
                lineHeight: 1.8,
                color: COLORS.textSecondary,
              }}
            >
              <ReactMarkdown
                components={{
                  h2: ({ children }) => (
                    <h2 style={{ color: COLORS.textPrimary, fontSize: 14, marginBottom: 8 }}>{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 style={{ color: COLORS.textPrimary, fontSize: 13, marginBottom: 6 }}>{children}</h3>
                  ),
                  strong: ({ children }) => (
                    <strong style={{ color: COLORS.textPrimary }}>{children}</strong>
                  ),
                  li: ({ children }) => (
                    <li style={{ color: COLORS.textSecondary, marginBottom: 4 }}>{children}</li>
                  ),
                  p: ({ children }) => (
                    <p style={{ margin: '6px 0', color: COLORS.textSecondary }}>{children}</p>
                  ),
                }}
              >
                {result.aiSummary}
              </ReactMarkdown>
            </div>
          </div>

          <Divider style={{ borderColor: '#252836', margin: '16px 0' }} />

          {/* Tomorrow focus */}
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.textPrimary,
                marginBottom: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <EyeOutlined style={{ color: COLORS.chartBlue }} />
              明日关注
            </div>
            <div
              style={{
                background: 'rgba(24,144,255,0.08)',
                border: `1px solid rgba(24,144,255,0.2)`,
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: 13,
                color: COLORS.textSecondary,
                lineHeight: 1.7,
              }}
            >
              {result.tomorrowFocus}
            </div>
          </div>

          {/* Risk warnings */}
          <div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.textPrimary,
                marginBottom: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <WarningOutlined style={{ color: COLORS.chartGold }} />
              风险提示
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {result.riskWarnings.map((warn, i) => (
                <div
                  key={i}
                  style={{
                    background: 'rgba(250,173,20,0.08)',
                    border: `1px solid rgba(250,173,20,0.2)`,
                    borderRadius: 6,
                    padding: '8px 12px',
                    fontSize: 12,
                    color: COLORS.textSecondary,
                    display: 'flex',
                    gap: 8,
                    alignItems: 'flex-start',
                  }}
                >
                  <WarningOutlined style={{ color: COLORS.chartGold, marginTop: 2 }} />
                  {warn}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
