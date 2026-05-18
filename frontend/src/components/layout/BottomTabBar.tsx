import { NavLink } from 'react-router-dom';
import { COLORS } from '../../constants/colors';

const tabs = [
  { path: '/', label: '行情', icon: '📊', end: true },
  { path: '/anomaly', label: '异动', icon: '⚡', end: false },
  { path: '/screening', label: '筛选', icon: '🔍', end: false },
];

export default function BottomTabBar() {
  return (
    <nav
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 56,
        background: COLORS.bgCard,
        borderTop: '1px solid #252836',
        display: 'flex',
        zIndex: 200,
        // safe area for iOS notch
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      {tabs.map((tab) => (
        <NavLink
          key={tab.path}
          to={tab.path}
          end={tab.end}
          style={({ isActive }) => ({
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textDecoration: 'none',
            color: isActive ? COLORS.chartRed : COLORS.textMuted,
            gap: 3,
            fontSize: 11,
            fontWeight: isActive ? 600 : 400,
            transition: 'color 0.2s',
          })}
        >
          <span style={{ fontSize: 22, lineHeight: 1 }}>{tab.icon}</span>
          <span>{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
