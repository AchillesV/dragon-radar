import { Spin, Empty, Result } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { COLORS } from '../../constants/colors';

interface LoadingStateProps {
  tip?: string;
  height?: number;
}

export function LoadingState({ tip = '加载中...', height = 200 }: LoadingStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height,
        color: COLORS.textSecondary,
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <Spin indicator={<LoadingOutlined style={{ fontSize: 32, color: COLORS.chartRed }} spin />} />
      <span style={{ fontSize: 13, color: COLORS.textMuted }}>{tip}</span>
    </div>
  );
}

interface EmptyStateProps {
  description?: string;
  height?: number;
}

export function EmptyState({ description = '暂无数据', height = 200 }: EmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height,
      }}
    >
      <Empty
        description={<span style={{ color: COLORS.textMuted }}>{description}</span>}
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    </div>
  );
}

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = '加载失败，请稍后重试', onRetry }: ErrorStateProps) {
  return (
    <Result
      status="error"
      title={<span style={{ color: COLORS.textSecondary }}>{message}</span>}
      extra={
        onRetry ? (
          <span
            style={{ color: COLORS.chartBlue, cursor: 'pointer', fontSize: 13 }}
            onClick={onRetry}
          >
            重新加载
          </span>
        ) : null
      }
    />
  );
}
