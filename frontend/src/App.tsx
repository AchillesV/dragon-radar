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
import { COLORS } from './constants/colors';
import { useIsMobile } from './hooks/useIsMobile';

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

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: theme.darkAlgorithm,
          token: {
            colorBgBase: COLORS.bgPrimary,
            colorBgContainer: COLORS.bgCard,
            colorBgElevated: COLORS.bgCard,
            colorBorder: '#3d4255',
            colorBorderSecondary: '#252836',
            colorText: COLORS.textPrimary,
            colorTextSecondary: COLORS.textSecondary,
            colorPrimary: COLORS.chartRed,
            borderRadius: 6,
            fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`,
          },
          components: {
            Table: {
              colorBgContainer: COLORS.bgCard,
              headerBg: '#252836',
              headerColor: COLORS.textSecondary,
              rowHoverBg: COLORS.bgHover,
              borderColor: '#252836',
              bodySortBg: 'transparent',
            },
            Modal: {
              contentBg: COLORS.bgCard,
              headerBg: COLORS.bgCard,
            },
            Select: {
              optionSelectedBg: COLORS.bgHover,
            },
            Tabs: {
              itemColor: COLORS.textSecondary,
              itemActiveColor: COLORS.chartRed,
              itemSelectedColor: COLORS.chartRed,
              inkBarColor: COLORS.chartRed,
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
              </Routes>
            </main>
            {isMobile && <BottomTabBar />}
          </div>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
