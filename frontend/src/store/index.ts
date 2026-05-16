import { create } from 'zustand';
import type { StockRow, FeatureTag } from '../types';

interface AppState {
  // Selected features for screening
  selectedFeatures: string[];
  setSelectedFeatures: (features: string[]) => void;

  // Stock table state
  stocks: StockRow[];
  setStocks: (stocks: StockRow[]) => void;
  updateStock: (code: string, updates: Partial<StockRow>) => void;

  // Filter state
  filters: Record<string, unknown>;
  setFilters: (filters: Record<string, unknown>) => void;

  // Column visibility
  hiddenColumns: string[];
  toggleColumn: (column: string) => void;

  // Feature tags
  featureTags: FeatureTag[];
  setFeatureTags: (tags: FeatureTag[]) => void;
}

const defaultFeatureTags: FeatureTag[] = [
  // ── 实时特征（涨停池数据，毫秒级响应）──────────────────────────────────
  { id: 'recent_limit',    name: '近期涨停',  description: '近5日内曾出现涨停',             isBuiltin: true,  isDefault: false },
  { id: 'lianban',         name: '连板股',    description: '当日处于连板状态（≥2板）',       isBuiltin: true,  isDefault: false },
  { id: 'lianban_upgrade', name: '连板升级',  description: '今日涨停且连板数≥2',            isBuiltin: true,  isDefault: false },
  { id: 'quiet_limit',     name: '缩量涨停',  description: '涨停且换手率<3%，筹码锁定',     isBuiltin: true,  isDefault: false },
  { id: 'rebound_limit',   name: '炸板回封',  description: '炸板后重新封涨停板',            isBuiltin: true,  isDefault: false },
  { id: 'volume_surge',    name: '量能异动',  description: '量比≥2.5且当日上涨',           isBuiltin: true,  isDefault: false },
  { id: 'high_turnover',   name: '高换手',    description: '换手率≥10%',                  isBuiltin: true,  isDefault: false },
  { id: 'weak_to_strong',  name: '弱转强',    description: '昨日涨停后今日继续上涨',        isBuiltin: true,  isDefault: false },
  { id: 'fund_inflow',     name: '大资金',    description: '当日成交额≥10亿（主力代理）',   isBuiltin: true,  isDefault: false },
  // ── 历史分析特征（腾讯日线接口，首次约5秒，缓存后<1秒）──────────────
  { id: 'multi_limit_15d', name: '多涨停',    description: '15个交易日内涨停板≥3次',       isBuiltin: false, isDefault: true  },
  { id: 'vol_surge_3d',    name: '近期放量',  description: '近3天至少一次3倍放量上涨',      isBuiltin: false, isDefault: false },
  { id: 'five_day_rally',  name: '5天连涨',   description: '最近5个交易日连续收涨',         isBuiltin: false, isDefault: false },
];

export const useAppStore = create<AppState>((set) => ({
  selectedFeatures: defaultFeatureTags.filter((t) => t.isDefault).map((t) => t.id),
  setSelectedFeatures: (features) => set({ selectedFeatures: features }),

  stocks: [],
  setStocks: (stocks) => set({ stocks }),
  updateStock: (code, updates) =>
    set((state) => ({
      stocks: state.stocks.map((s) => (s.code === code ? { ...s, ...updates } : s)),
    })),

  filters: {},
  setFilters: (filters) => set({ filters }),

  hiddenColumns: [],
  toggleColumn: (column) =>
    set((state) => ({
      hiddenColumns: state.hiddenColumns.includes(column)
        ? state.hiddenColumns.filter((c) => c !== column)
        : [...state.hiddenColumns, column],
    })),

  featureTags: defaultFeatureTags,
  setFeatureTags: (tags) => set({ featureTags: tags }),
}));
