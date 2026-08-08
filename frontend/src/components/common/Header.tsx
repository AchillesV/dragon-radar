import { NavLink } from 'react-router-dom';
import { Space, Button, Tooltip } from 'antd';
import { BulbOutlined, BulbFilled } from '@ant-design/icons';
import dayjs from 'dayjs';
import { COLORS } from '../../constants/colors';
import { useMarketOverview } from '../../hooks/useMarketData';
import { useIsMobile } from '../../hooks/useIsMobile';
import { useTheme } from '../../hooks/useTheme';

const navItems = [
  { path: '/', label: '行情总览' },
  { path: '/anomaly', label: '异动监控' },
  { path: '/screening', label: '特征筛选' },
  { path: '/trend', label: '趋势' },
  { path: '/mainline', label: '主线' },
];

const statusColors: Record<string, string> = {
  pre: '#faad14',
  trading: '#52c41a',
  closed: '#8b949e',
};

const statusLabels: Record<string, string> = {
  pre: '盘前',
  trading: '交易中',
  closed: '已收盘',
};

export default function Header() {
  const { data: overview } = useMarketOverview();
  const marketStatus = overview?.marketStatus ?? 'closed';
  const isMobile = useIsMobile();
  const { theme: currentTheme, toggle } = useTheme();
  const isDark = currentTheme === 'dark';

  return (
    <header
      style={{
        background: COLORS.bgPrimary,
        borderBottom: `1px solid var(--c-border)`,
        padding: isMobile ? '0 16px' : '0 24px',
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 8 : 12 }}>
        <span style={{ fontSize: isMobile ? 24 : 28 }}>🐉</span>
        <span
          style={{
            fontSize: isMobile ? 16 : 18,
            fontWeight: 700,
            color: COLORS.textPrimary,
            letterSpacing: isMobile ? 1 : 2,
          }}
        >
          龙头雷达
        </span>
        {!isMobile && (
          <span
            style={{
              fontSize: 11,
              color: COLORS.textMuted,
              border: `1px solid var(--c-text-muted)`,
              borderRadius: 3,
              padding: '1px 5px',
              letterSpacing: 1,
            }}
          >
            DragonRadar
          </span>
        )}
      </div>

      {/* Navigation — desktop only, mobile uses BottomTabBar */}
      {!isMobile && (
        <nav style={{ display: 'flex', gap: 8 }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              style={({ isActive }) => ({
                color: isActive ? COLORS.chartRed : COLORS.textSecondary,
                textDecoration: 'none',
                padding: '6px 16px',
                borderRadius: 6,
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                background: isActive ? 'rgba(255,77,79,0.12)' : 'transparent',
                border: isActive ? `1px solid rgba(255,77,79,0.3)` : '1px solid transparent',
                transition: 'all 0.2s',
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}

      {/* Right: theme toggle + date + status */}
      <Space size={isMobile ? 6 : 16}>
        <Tooltip title={isDark ? '切换亮色' : '切换暗色'}>
          <Button
            type="text"
            size="small"
            icon={isDark ? <BulbOutlined /> : <BulbFilled />}
            onClick={toggle}
            style={{ color: COLORS.textSecondary }}
          />
        </Tooltip>
        {!isMobile && (
          <span style={{ color: COLORS.textSecondary, fontSize: 13 }}>
            {dayjs().format('YYYY-MM-DD')}
          </span>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: statusColors[marketStatus],
              boxShadow: `0 0 6px ${statusColors[marketStatus]}`,
            }}
          />
          <span style={{ color: COLORS.textSecondary, fontSize: 13 }}>
            {statusLabels[marketStatus]}
          </span>
        </div>
      </Space>
    </header>
  );
}
