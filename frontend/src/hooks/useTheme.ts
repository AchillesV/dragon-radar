import { create } from 'zustand';
import { DARK_COLORS_RAW, LIGHT_COLORS_RAW, type RawColors } from '../constants/colors';

type Theme = 'dark' | 'light';

interface ThemeStore {
  theme: Theme;
  toggle: () => void;
  rawColors: RawColors;
}

const saved = (localStorage.getItem('theme') as Theme) ?? 'dark';

export const useTheme = create<ThemeStore>((set, get) => ({
  theme: saved,
  rawColors: saved === 'light' ? LIGHT_COLORS_RAW : DARK_COLORS_RAW,
  toggle: () => {
    const next: Theme = get().theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    set({ theme: next, rawColors: next === 'light' ? LIGHT_COLORS_RAW : DARK_COLORS_RAW });
  },
}));
