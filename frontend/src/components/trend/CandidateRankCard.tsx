import { Card, Tag, Tooltip } from 'antd';
import { COLORS } from '../../constants/colors';
import { formatChangePct } from '../../utils/format';
import type { TrendStockScore } from '../../types';
import { starsOf, scoreColor } from './SectorHeatCard';

function Mini({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 46 }}>
      <span style={{ fontSize: 11, color: COLORS.textMuted }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: color ?? COLORS.textPrimary }}>{value}</span>
    </div>
  );
}

function chgColor(v?: number): string {
  if (v === undefined) return COLORS.textMuted;
  return v > 0 ? COLORS.rise : v < 0 ? COLORS.fall : COLORS.textSecondary;
}

const ROLE_COLOR: Record<string, string> = {
  '龙头': 'red',
  '核心中军': 'volcano',
  '趋势跟随': 'blue',
  '补涨': 'default',
};

const BUY_COLOR: Record<string, string> = {
  BREAKOUT: 'red',
  RESTART: 'volcano',
  PULLBACK: 'green',
  TREND: 'blue',
  ACCELERATION: 'orange',
  OVERHEATED: 'gold',
  EXIT_RISK: 'default',
  WAIT: 'default',
};

/** 候选池里单只重点股（Phase 2：Smart Money / RS / Freshness） */
export default function CandidateRankCard({
  stock,
  rank,
  onClick,
}: {
  stock: TrendStockScore;
  rank?: number;
  onClick?: () => void;
}) {
  const s = starsOf(stock.score);
  return (
    <Card
      size="small"
      hoverable={!!onClick}
      onClick={onClick}
      styles={{ body: { padding: '12px 14px' } }}
      style={{
        background: COLORS.bgCard,
        border: `1px solid ${rank === 1 ? COLORS.chartRed : 'var(--c-border)'}`,
        marginBottom: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flexWrap: 'wrap' }}>
          {rank !== undefined && (
            <span style={{
              fontSize: 13, fontWeight: 700, color: rank <= 3 ? COLORS.chartRed : COLORS.textMuted, minWidth: 18,
            }}>
              {rank}
            </span>
          )}
          <span style={{ fontSize: 15, fontWeight: 700, color: COLORS.textPrimary, whiteSpace: 'nowrap' }}>
            {stock.name}
          </span>
          <span style={{ fontSize: 12, color: COLORS.textMuted }}>{stock.code}</span>
          {stock.isCore && <Tag color="red" style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}>核心</Tag>}
          {stock.isPick && <Tag color="gold" style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}>★标的</Tag>}
          {stock.buyStatusLabel && (
            <Tag color={BUY_COLOR[stock.buyStatus] ?? 'default'} style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}>
              {stock.buyStatusLabel}
            </Tag>
          )}
          {stock.ladderRole && (
            <Tag color={ROLE_COLOR[stock.ladderRole] ?? 'default'} style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}>
              {stock.ladderRole}
            </Tag>
          )}
          {stock.sector && <Tag color="blue" style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}>{stock.sector}</Tag>}
          {stock.concept && <Tag color="magenta" style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}>{stock.concept}</Tag>}
        </div>
        <div style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: scoreColor(stock.score), lineHeight: 1 }}>
            {stock.score.toFixed(1)}
          </div>
          <div style={{ fontSize: 11, color: COLORS.chartGold, letterSpacing: 1 }}>
            {'★'.repeat(s)}{'☆'.repeat(5 - s)}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
        <Mini label="今日" value={formatChangePct(stock.changePct)} color={chgColor(stock.changePct)} />
        <Mini label="5日" value={stock.ret5Pct === undefined ? '--' : formatChangePct(stock.ret5Pct)} color={chgColor(stock.ret5Pct)} />
        <Tooltip title="资金行为评分（0~100）">
          <div style={{ display: 'flex' }}><Mini label="Smart Money" value={stock.smartMoneyScore.toFixed(0)} /></div>
        </Tooltip>
        <Tooltip title="核心股评分（板块内相对强度/资金/成交额/趋势/抗跌…）">
          <div style={{ display: 'flex' }}><Mini label="核心分" value={stock.coreScore.toFixed(0)} /></div>
        </Tooltip>
        <Mini label="相对强度" value={stock.rsScore.toFixed(0)} />
        <Mini label="新鲜度" value={stock.freshness.toFixed(0)} />
        <Mini label="距启动" value={`${stock.breakoutDays}日`} />
        {stock.lifecycleLabel && <Mini label="资金阶段" value={stock.lifecycleLabel} />}
      </div>

      {stock.signals.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {stock.signals.map((sig) => (
            <Tag key={sig} color="orange" style={{ marginInlineEnd: 0, fontSize: 11 }}>{sig}</Tag>
          ))}
        </div>
      )}
    </Card>
  );
}

function CompBar({ label, value, hint }: { label: string; value?: number; hint?: string }) {
  const v = value ?? 0;
  const color = v >= 75 ? COLORS.chartRed : v >= 55 ? COLORS.chartGold : COLORS.chartBlue;
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: COLORS.textSecondary, marginBottom: 3 }}>
        <span>{label}{hint && <span style={{ color: COLORS.textMuted, fontSize: 11 }}> · {hint}</span>}</span>
        <span style={{ color, fontWeight: 600 }}>{v.toFixed(0)}</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: COLORS.bgHover, overflow: 'hidden' }}>
        <div style={{ width: `${Math.max(2, Math.min(100, v))}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
}

/** 重点股详情（Drawer 内容） */
export function CandidateDetail({ stock }: { stock: TrendStockScore }) {
  const c = stock.components ?? {};
  const s = starsOf(stock.score);
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 20, fontWeight: 800, color: scoreColor(stock.score) }}>{stock.score.toFixed(1)}</span>
        <span style={{ color: COLORS.chartGold, fontSize: 14 }}>{'★'.repeat(s)}{'☆'.repeat(5 - s)}</span>
        <span style={{ fontSize: 13, color: COLORS.textMuted }}>综合评分 FinalScore</span>
      </div>
      <div style={{ fontSize: 12, color: COLORS.textMuted, marginBottom: 14 }}>
        {stock.sector && <Tag color="blue">行业：{stock.sector}</Tag>}
        {stock.concept && <Tag color="magenta">概念：{stock.concept}</Tag>}
        {stock.ladderRole && <Tag color={ROLE_COLOR[stock.ladderRole] ?? 'default'}>梯队：{stock.ladderRole}</Tag>}
        {stock.rankInSector && <Tag>板块内第 {stock.rankInSector}/{stock.sectorSize}</Tag>}
        {stock.breakoutDate && <span>放量启动 {stock.breakoutDate}（{stock.breakoutDays} 个交易日前）</span>}
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        <Mini label="今日" value={formatChangePct(stock.changePct)} color={chgColor(stock.changePct)} />
        <Mini label="近5日" value={stock.ret5Pct === undefined ? '--' : formatChangePct(stock.ret5Pct)} color={chgColor(stock.ret5Pct)} />
        <Mini label="Smart Money" value={stock.smartMoneyScore.toFixed(0)} />
        <Mini label="核心分" value={stock.coreScore.toFixed(0)} />
        <Mini label="相对强度 RS" value={stock.rsScore.toFixed(0)} />
        <Mini label="新鲜度" value={stock.freshness.toFixed(0)} />
      </div>

      {stock.lifecyclePath.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 12, color: COLORS.textMuted, marginBottom: 6 }}>资金生命周期</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', fontSize: 13 }}>
            {stock.lifecyclePath.map((p, i) => (
              <span key={`${p}-${i}`} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {i > 0 && <span style={{ color: COLORS.textMuted }}>→</span>}
                <span style={{
                  color: i === stock.lifecyclePath.length - 1 ? COLORS.chartRed : COLORS.textSecondary,
                  fontWeight: i === stock.lifecyclePath.length - 1 ? 700 : 400,
                }}>
                  {i === stock.lifecyclePath.length - 1 ? `★ ${p} · 当前` : p}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <span style={{ fontSize: 12, color: COLORS.textMuted, marginRight: 6 }}>当前状态</span>
        <Tag color={BUY_COLOR[stock.buyStatus] ?? 'default'}>{stock.buyStatusLabel || '—'}</Tag>
        {stock.buyStatus === 'ACCELERATION' && <span style={{ fontSize: 11, color: COLORS.textMuted }}>加速拉升，不建议追高</span>}
        {stock.buyStatus === 'OVERHEATED' && <span style={{ fontSize: 11, color: COLORS.textMuted }}>高位分歧，注意波动</span>}
        {stock.buyStatus === 'EXIT_RISK' && <span style={{ fontSize: 11, color: COLORS.textMuted }}>跌破结构，注意风险</span>}
      </div>

      <div style={{ fontSize: 12, color: COLORS.textMuted, marginBottom: 8 }}>核心股评分构成（CoreScore）</div>
      <CompBar label="板块内相对强度" value={c.sectorRelative} hint="权重 20%" />
      <CompBar label="资金强度（板块代理）" value={c.netInflow} hint="权重 15%" />
      <CompBar label="成交额" value={c.amount} hint="权重 15%" />
      <CompBar label="趋势完整性" value={c.trendIntegrity} hint="权重 10%" />
      <CompBar label="放量启动质量" value={c.breakoutQuality} hint="权重 10%" />
      <CompBar label="抗跌能力（缩量回调）" value={c.resilience} hint="权重 10%" />
      <CompBar label="板块共振" value={c.sectorResonance} hint="权重 10%" />
      <CompBar label="市场关注度（换手）" value={c.attention} hint="权重 5%" />

      <div style={{ fontSize: 12, color: COLORS.textMuted, margin: '12px 0 8px' }}>资金行为评分构成（Smart Money）</div>
      <CompBar label="放量启动质量" value={c.breakoutQuality} hint="权重 15%" />
      <CompBar label="启动后量能保持" value={c.volumeSustain} hint="权重 10%" />
      <CompBar label="个股相对强度" value={c.relativeStrength} hint="权重 15%" />
      <CompBar label="板块共振" value={c.sectorResonance} hint="权重 15%" />
      <CompBar label="资金（板块级代理）" value={c.netInflow} hint="权重 10%" />
      <CompBar label="回调资金稳定性" value={c.resilience} hint="权重 10%" />
      <CompBar label="再次放量突破" value={c.restart} hint="权重 10%" />
      <CompBar label="新高/突破" value={c.newHigh} hint="权重 5%" />
      <CompBar label="资金信号新鲜度" value={c.freshness} hint="权重 10%" />

      {stock.signals.length > 0 && (
        <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {stock.signals.map((sig) => <Tag key={sig} color="orange">{sig}</Tag>)}
        </div>
      )}

      <div style={{ marginTop: 14, fontSize: 11, color: COLORS.textMuted, lineHeight: 1.7 }}>
        ⚠️ 以上为策略信号与条件触发指标，不构成买入/卖出建议。资金维度用「所属行业板块主力净额/成交额」
        做代理（不接逐股净流入）；相对强度对标 沪深300 / 中证1000 / 行业 /（命中概念）。
      </div>
    </div>
  );
}
