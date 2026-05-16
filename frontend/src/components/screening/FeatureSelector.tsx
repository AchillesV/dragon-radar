import { useState } from 'react';
import { Tag, Button, Modal, Form, Input, Select, Divider, Tooltip } from 'antd';
import { PlusOutlined, HistoryOutlined } from '@ant-design/icons';
import { useAppStore } from '../../store';
import { COLORS } from '../../constants/colors';
import type { FeatureTag } from '../../types';

const { CheckableTag } = Tag;

export default function FeatureSelector() {
  const { featureTags, selectedFeatures, setSelectedFeatures, setFeatureTags } = useAppStore();
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [form] = Form.useForm();

  const handleToggle = (id: string, checked: boolean) => {
    if (checked) {
      setSelectedFeatures([...selectedFeatures, id]);
    } else {
      setSelectedFeatures(selectedFeatures.filter((f) => f !== id));
    }
  };

  const handleAddCustom = (values: { name: string; description: string; condition: string }) => {
    const newTag: FeatureTag = {
      id: `custom_${Date.now()}`,
      name: values.name,
      description: values.description || values.condition,
      isBuiltin: false,
      isDefault: false,
    };
    setFeatureTags([...featureTags, newTag]);
    setShowCustomModal(false);
    form.resetFields();
  };

  const builtinTags = featureTags.filter((t) => t.isBuiltin);
  const customTags = featureTags.filter((t) => !t.isBuiltin);

  return (
    <div
      style={{
        background: COLORS.bgCard,
        borderRadius: 8,
        padding: '16px',
        marginBottom: 16,
      }}
    >
      <div
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: COLORS.textSecondary,
          marginBottom: 10,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        特征筛选条件
        <span
          style={{
            fontSize: 11,
            background: 'rgba(24,144,255,0.12)',
            color: COLORS.chartBlue,
            borderRadius: 3,
            padding: '1px 6px',
          }}
        >
          已选 {selectedFeatures.length} 项
        </span>
      </div>

      {/* 实时特征 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
        {builtinTags.map((tag) => (
          <Tooltip key={tag.id} title={tag.description} mouseEnterDelay={0.5}>
            <CheckableTag
              checked={selectedFeatures.includes(tag.id)}
              onChange={(checked) => handleToggle(tag.id, checked)}
              style={{
                fontSize: 12,
                padding: '3px 10px',
                borderRadius: 4,
                border: selectedFeatures.includes(tag.id)
                  ? `1px solid ${COLORS.chartRed}`
                  : `1px solid #3d4255`,
                background: selectedFeatures.includes(tag.id)
                  ? 'rgba(255,77,79,0.15)'
                  : 'transparent',
                color: selectedFeatures.includes(tag.id)
                  ? COLORS.chartRed
                  : COLORS.textSecondary,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {tag.name}
            </CheckableTag>
          </Tooltip>
        ))}
      </div>

      {/* 历史分析特征 */}
      <div style={{ marginTop: 10 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 8,
          color: COLORS.textSecondary,
          fontSize: 11,
        }}>
          <HistoryOutlined />
          <span>历史分析</span>
          <span style={{ color: '#4a5568' }}>首次加载约5秒，缓存1小时</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          {customTags.map((tag) => (
            <Tooltip key={tag.id} title={tag.description} mouseEnterDelay={0.5}>
              <CheckableTag
                checked={selectedFeatures.includes(tag.id)}
                onChange={(checked) => handleToggle(tag.id, checked)}
                style={{
                  fontSize: 12,
                  padding: '3px 10px',
                  borderRadius: 4,
                  border: selectedFeatures.includes(tag.id)
                    ? `1px solid ${COLORS.chartGold}`
                    : `1px solid #3d4255`,
                  background: selectedFeatures.includes(tag.id)
                    ? 'rgba(250,173,20,0.15)'
                    : 'transparent',
                  color: selectedFeatures.includes(tag.id)
                    ? COLORS.chartGold
                    : COLORS.textSecondary,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                {tag.name}
              </CheckableTag>
            </Tooltip>
          ))}

          <Divider type="vertical" style={{ borderColor: '#3d4255', height: 20 }} />

          <Button
            size="small"
            icon={<PlusOutlined />}
            onClick={() => setShowCustomModal(true)}
            style={{
              fontSize: 12,
              borderColor: '#3d4255',
              color: COLORS.textMuted,
              background: 'transparent',
            }}
          >
            自定义特征
          </Button>
        </div>
      </div>

      {/* Custom feature modal */}
      <Modal
        title={<span style={{ color: COLORS.textPrimary }}>添加自定义特征</span>}
        open={showCustomModal}
        onCancel={() => setShowCustomModal(false)}
        onOk={() => form.submit()}
        okText="添加"
        cancelText="取消"
        styles={{
          content: { background: COLORS.bgCard },
          header: { background: COLORS.bgCard, borderBottom: '1px solid #252836' },
          footer: { borderTop: '1px solid #252836' },
        }}
      >
        <Form form={form} onFinish={handleAddCustom} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label={<span style={{ color: COLORS.textSecondary }}>特征名称</span>}
            rules={[{ required: true, message: '请输入特征名称' }]}
          >
            <Input
              placeholder="例如：近5日涨停"
              style={{ background: '#252836', borderColor: '#3d4255', color: COLORS.textPrimary }}
            />
          </Form.Item>
          <Form.Item
            name="condition"
            label={<span style={{ color: COLORS.textSecondary }}>筛选条件</span>}
            rules={[{ required: true, message: '请选择筛选条件' }]}
          >
            <Select
              placeholder="选择筛选维度"
              style={{ width: '100%' }}
              options={[
                { label: '近N日涨停次数 ≥ X', value: 'limit_up_count' },
                { label: '换手率 ≥ X%', value: 'turnover_gte' },
                { label: '成交额 ≥ X亿', value: 'amount_gte' },
                { label: '量比 ≥ X', value: 'volume_ratio_gte' },
                { label: '涨幅 ≥ X%', value: 'change_pct_gte' },
                { label: '属于特定板块', value: 'sector_in' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={<span style={{ color: COLORS.textSecondary }}>备注说明（可选）</span>}
          >
            <Input.TextArea
              rows={2}
              placeholder="描述该特征的含义"
              style={{ background: '#252836', borderColor: '#3d4255', color: COLORS.textPrimary }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
