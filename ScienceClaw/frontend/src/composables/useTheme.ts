import { ref } from 'vue';

const THEME_KEY = 'scienceclaw-theme';
const isDark = ref(false);

export function useTheme() {
  const toggleTheme = () => {
    isDark.value = !isDark.value;
    updateTheme();
  };

  const updateTheme = () => {
    const html = document.documentElement;
    if (isDark.value) {
      html.classList.add('dark');
      localStorage.setItem(THEME_KEY, 'dark');
    } else {
      html.classList.remove('dark');
      localStorage.setItem(THEME_KEY, 'light');
    }
  };

  const initTheme = () => {
    const savedTheme = localStorage.getItem(THEME_KEY);
    if (savedTheme === 'dark') {
      isDark.value = true;
    } else if (savedTheme === 'light') {
      isDark.value = false;
    } else {
      // Check system preference
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    updateTheme();
  };

  return {
    isDark,
    toggleTheme,
    initTheme
  };
}
