import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import zhCN from 'antd/locale/zh_CN';
import Header from './components/common/Header';
import BottomTabBar from './components/layout/BottomTabBar';
import Dashboard from './pages/Dashboard';
import AnomalyMonitor from './pages/AnomalyMonitor';
import AnomalyDetail from './pages/AnomalyDetail';
import Screening from './pages/Screening';
import Trend from './pages/Trend';
import { COLORS } from './constants/colors';
import { useIsMobile } from './hooks/useIsMobile';
import { useTheme } from './hooks/useTheme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30000,
    },
  },
});

export default function App() {
  const isMobile = useIsMobile();
  const { theme: currentTheme, rawColors } = useTheme();
  const isDark = currentTheme === 'dark';

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.remove('theme-light');
    } else {
      document.documentElement.classList.add('theme-light');
    }
  }, [isDark]);

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorBgBase: rawColors.bgPrimary,
            colorBgContainer: rawColors.bgCard,
            colorBgElevated: rawColors.bgCard,
            colorBorder: rawColors.borderLight,
            colorBorderSecondary: rawColors.border,
            colorText: rawColors.textPrimary,
            colorTextSecondary: rawColors.textSecondary,
            colorPrimary: rawColors.chartRed,
            borderRadius: 6,
            fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`,
          },
          components: {
            Table: {
              colorBgContainer: rawColors.bgCard,
              headerBg: rawColors.border,
              headerColor: rawColors.textSecondary,
              rowHoverBg: rawColors.bgHover,
              borderColor: rawColors.border,
              bodySortBg: 'transparent',
            },
            Modal: {
              contentBg: rawColors.bgCard,
              headerBg: rawColors.bgCard,
            },
            Select: {
              optionSelectedBg: rawColors.bgHover,
            },
            Tabs: {
              itemColor: rawColors.textSecondary,
              itemActiveColor: rawColors.chartRed,
              itemSelectedColor: rawColors.chartRed,
              inkBarColor: rawColors.chartRed,
            },
          },
        }}
      >
        <BrowserRouter>
          <div style={{ minHeight: '100vh', background: COLORS.bgPrimary }}>
            <Header />
            <main
              style={{
                padding: isMobile ? '12px 12px 72px' : '24px',
                background: COLORS.bgPrimary,
                minHeight: 'calc(100vh - 56px)',
              }}
            >
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/anomaly" element={<AnomalyMonitor />} />
                <Route path="/anomaly/:type" element={<AnomalyDetail />} />
                <Route path="/screening" element={<Screening />} />
                <Route path="/trend" element={<Trend />} />
              </Routes>
            </main>
            {isMobile && <BottomTabBar />}
          </div>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
