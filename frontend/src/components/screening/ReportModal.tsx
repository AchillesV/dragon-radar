import { Modal, Rate, Divider } from 'antd';
import ReactMarkdown from 'react-markdown';
import type { StockReport } from '../../types';
import { COLORS } from '../../constants/colors';

interface ReportModalProps {
  report: StockReport | null;
  open: boolean;
  onClose: () => void;
}

export default function ReportModal({ report, open, onClose }: ReportModalProps) {
  if (!report) return null;

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 16, fontWeight: 700, color: COLORS.textPrimary }}>
            {report.stockName}
          </span>
          <span
            style={{
              fontSize: 12,
              color: COLORS.textMuted,
              background: '#252836',
              borderRadius: 4,
              padding: '2px 8px',
            }}
          >
            {report.stockCode}
          </span>
          <span style={{ fontSize: 12, color: COLORS.textMuted }}>深度分析报告</span>
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={800}
      styles={{
        content: {
          background: COLORS.bgCard,
          padding: 0,
          maxHeight: '85vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        },
        header: {
          background: COLORS.bgCard,
          borderBottom: `1px solid #252836`,
          padding: '16px 24px',
          margin: 0,
        },
        body: {
          padding: 0,
          overflow: 'auto',
          flex: 1,
        },
      }}
    >
      {/* Scores */}
      {report.scores && (
        <div
          style={{
            display: 'flex',
            gap: 24,
            padding: '12px 24px',
            background: '#252836',
            borderBottom: `1px solid #1a1d29`,
          }}
        >
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>强度评分</div>
            <Rate
              disabled
              value={Math.round((report.scores.strength / 100) * 5)}
              style={{ fontSize: 14, color: COLORS.chartRed }}
            />
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>确定性</div>
            <Rate
              disabled
              value={Math.round((report.scores.certainty / 100) * 5)}
              style={{ fontSize: 14, color: COLORS.chartGold }}
            />
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 4 }}>风险收益比</div>
            <Rate
              disabled
              value={Math.round((report.scores.riskRatio / 100) * 5)}
              style={{ fontSize: 14, color: COLORS.chartGreen }}
            />
          </div>
        </div>
      )}

      {/* Sections */}
      <div style={{ padding: '16px 24px', overflow: 'auto' }}>
        {report.sections.map((section, i) => (
          <div key={i} style={{ marginBottom: 24 }}>
            <div
              style={{
                fontSize: 14,
                fontWeight: 700,
                color: COLORS.textPrimary,
                marginBottom: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <div
                style={{
                  width: 3,
                  height: 16,
                  background: COLORS.chartRed,
                  borderRadius: 2,
                  flexShrink: 0,
                }}
              />
              {section.title}
            </div>
            <div
              style={{
                fontSize: 13,
                lineHeight: 1.8,
                color: COLORS.textSecondary,
              }}
            >
              <ReactMarkdown
                components={{
                  p: ({ children }) => (
                    <p style={{ margin: '6px 0', color: COLORS.textSecondary }}>{children}</p>
                  ),
                  strong: ({ children }) => (
                    <strong style={{ color: COLORS.textPrimary }}>{children}</strong>
                  ),
                  li: ({ children }) => (
                    <li style={{ color: COLORS.textSecondary, marginBottom: 4 }}>{children}</li>
                  ),
                  h3: ({ children }) => (
                    <h3 style={{ color: COLORS.textPrimary, fontSize: 13, marginBottom: 8 }}>{children}</h3>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote
                      style={{
                        borderLeft: `3px solid ${COLORS.chartGold}`,
                        paddingLeft: 12,
                        margin: '8px 0',
                        color: COLORS.textSecondary,
                        background: 'rgba(250,173,20,0.05)',
                        padding: '8px 12px',
                        borderRadius: '0 4px 4px 0',
                      }}
                    >
                      {children}
                    </blockquote>
                  ),
                }}
              >
                {section.content}
              </ReactMarkdown>
            </div>
            {i < report.sections.length - 1 && (
              <Divider style={{ borderColor: '#252836', margin: '16px 0 0' }} />
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '10px 24px',
          borderTop: `1px solid #252836`,
          fontSize: 11,
          color: COLORS.textMuted,
        }}
      >
        生成时间：{report.generatedAt} · 本报告由AI生成，仅供参考，不构成投资建议
      </div>
    </Modal>
  );
}
