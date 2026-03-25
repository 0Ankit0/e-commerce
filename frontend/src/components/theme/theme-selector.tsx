'use client';

import { Palette } from 'lucide-react';
import { getAllThemes } from '@/lib/themes';
import { useThemeStore } from '@/store/theme-store';

export function ThemeSelector() {
  const activeThemeId = useThemeStore((state) => state.activeThemeId);
  const customThemes = useThemeStore((state) => state.customThemes);
  const setActiveTheme = useThemeStore((state) => state.setActiveTheme);
  const themes = getAllThemes(customThemes);

  return (
    <label className="flex items-center gap-2 rounded-lg border border-[var(--border-color)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-secondary)]">
      <Palette className="h-4 w-4 text-[var(--accent)]" />
      <span className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">
        Theme
      </span>
      <select
        value={activeThemeId}
        onChange={(event) => setActiveTheme(event.target.value)}
        className="min-w-32 bg-transparent text-sm font-medium text-[var(--text-primary)] outline-none"
        aria-label="Select theme"
      >
        {themes.map((theme) => (
          <option key={theme.id} value={theme.id}>
            {theme.name}
            {theme.isCustom ? ' (Custom)' : ''}
          </option>
        ))}
      </select>
    </label>
  );
}
