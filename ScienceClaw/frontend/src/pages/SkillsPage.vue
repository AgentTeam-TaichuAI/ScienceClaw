<template>
  <div class="flex flex-col h-full w-full overflow-hidden">
    <div class="flex-shrink-0 relative overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-br from-violet-600 via-fuchsia-600 to-pink-600"></div>
      <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNCI+PHBhdGggZD0iTTM2IDM0djZoLTZ2LTZoNnptMC0zMHY2aC02VjRoNnoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-50"></div>
      <div class="relative px-6 py-5">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-xl font-bold text-white flex items-center gap-2">
              <span class="inline-flex items-center justify-center size-8 rounded-lg bg-white/15 backdrop-blur-sm">
                <svg class="size-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
              </span>
              {{ t('Skills Library') }}
            </h1>
            <p class="text-white/60 text-xs mt-1">{{ skills.length }} skills installed</p>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="openInstallModal"
              class="inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-3 py-2 text-sm font-medium text-white backdrop-blur-sm transition-all duration-200 hover:bg-white/15 hover:border-white/25"
            >
              <Download :size="14" />
              <span>Install Skill</span>
            </button>
            <div class="relative group">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 size-4 group-focus-within:text-white/70 transition-colors" />
              <input v-model="searchQuery" type="text" :placeholder="t('Search skills...')"
                class="w-64 bg-white/10 backdrop-blur-sm border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:bg-white/15 focus:border-white/25 focus:ring-1 focus:ring-white/20 transition-all duration-200">
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-5 bg-[#f8f9fb] dark:bg-[#111]">
      <div v-if="skills.length === 0 && !loading" class="flex flex-col items-center justify-center h-full text-[var(--text-tertiary)] gap-3">
        <div class="size-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
          <Box :size="28" class="text-gray-300 dark:text-gray-600" />
        </div>
        <span class="text-sm">{{ t('No external skills installed') }}</span>
        <p class="text-xs opacity-60">Use Install Skill or the chat with find-skills to add one</p>
      </div>

      <div v-else-if="loading" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4 max-w-[1800px] mx-auto">
        <div v-for="i in 8" :key="i" class="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-[#1e1e1e] p-4 animate-pulse">
          <div class="flex items-start gap-3 mb-3">
            <div class="size-10 rounded-xl bg-gray-200 dark:bg-gray-700"></div>
            <div class="flex-1 space-y-2"><div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div><div class="h-3 bg-gray-100 dark:bg-gray-800 rounded w-1/2"></div></div>
          </div>
          <div class="space-y-2"><div class="h-3 bg-gray-100 dark:bg-gray-800 rounded"></div><div class="h-3 bg-gray-100 dark:bg-gray-800 rounded w-4/5"></div></div>
        </div>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4 max-w-[1800px] mx-auto">
        <div v-for="(skill, idx) in filteredSkills" :key="skill.name"
          class="skill-card group relative rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-[#1e1e1e] cursor-pointer overflow-hidden"
          :style="{ '--delay': `${Math.min(idx, 20) * 30}ms` }"
          @click="openSkill(skill)">
          <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
            <div class="absolute -inset-px rounded-xl bg-gradient-to-r from-violet-400/20 via-fuchsia-400/20 to-pink-400/20"></div>
          </div>
          <div class="relative p-4">
            <div class="flex items-start gap-3 mb-2.5">
              <div class="size-10 rounded-xl flex items-center justify-center text-white text-sm font-bold flex-shrink-0 shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3"
                :style="{ background: getSkillGradient(skill.name) }">
                {{ skill.name.charAt(0).toUpperCase() }}
              </div>
              <div class="min-w-0 flex-1">
                <h3 class="text-sm font-semibold text-[var(--text-primary)] truncate group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-violet-600 group-hover:to-fuchsia-600 transition-all duration-300">
                  {{ skill.name }}
                </h3>
                <p v-if="skill.description" class="mt-1 text-[11px] leading-5 text-[var(--text-tertiary)] line-clamp-2">
                  {{ skill.description }}
                </p>
              </div>
              <div v-if="!skill.builtin" class="flex items-center gap-0.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <button @click.stop="handleToggleBlock(skill)" class="p-1.5 rounded-lg transition-colors"
                  :class="skill.blocked ? 'text-amber-500 bg-amber-50 dark:bg-amber-900/20' : 'text-[var(--text-tertiary)] hover:bg-gray-100 dark:hover:bg-gray-800'">
                  <EyeOff v-if="skill.blocked" :size="13" /><Eye v-else :size="13" />
                </button>
                <button @click.stop="confirmDeleteSkill(skill)" class="p-1.5 rounded-lg text-[var(--text-tertiary)] hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 transition-colors">
                  <Trash2 :size="13" />
                </button>
              </div>
            </div>

            <div class="flex flex-wrap gap-1.5 min-h-[2rem] mb-3">
              <span v-for="badge in getSkillBadges(skill).slice(0, 5)" :key="`${skill.name}-${badge}`"
                class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium bg-violet-50 text-violet-700 dark:bg-violet-900/20 dark:text-violet-300">
                {{ badge }}
              </span>
            </div>

            <div class="space-y-0.5 text-[10px] font-mono text-[var(--text-tertiary)] min-h-[2.5rem]">
              <div v-for="file in (skill.files || []).slice(0, 3)" :key="file" class="flex items-center gap-1.5 truncate">
                <span class="opacity-40">{{ file.endsWith('/') ? '📁' : '📄' }}</span>
                <span>{{ file }}</span>
              </div>
              <div v-if="(skill.files || []).length > 3" class="opacity-40">+{{ skill.files.length - 3 }} more</div>
            </div>

            <div class="mt-3 flex items-center justify-between">
              <span v-if="skill.builtin" class="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium">Built-in</span>
              <span v-else-if="skill.blocked" class="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 font-medium">Blocked</span>
              <span v-else class="text-[10px] text-[var(--text-tertiary)]">{{ getSkillFooter(skill) }}</span>
              <div class="text-[10px] text-violet-500 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-1 group-hover:translate-x-0 flex items-center gap-0.5">
                Open <svg class="size-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" /></svg>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!loading && skills.length > 0 && filteredSkills.length === 0" class="flex flex-col items-center justify-center py-20 gap-3">
        <div class="size-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
          <Search :size="28" class="text-gray-300 dark:text-gray-600" />
        </div>
        <p class="text-sm text-[var(--text-tertiary)]">No skills match "{{ searchQuery }}"</p>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="modal">
        <div v-if="installOpen" class="fixed inset-0 z-[9999] flex items-center justify-center">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeInstallModal"></div>
          <div class="relative bg-white dark:bg-[#2a2a2a] rounded-2xl shadow-2xl p-6 w-[520px] max-w-[calc(100vw-2rem)] z-10">
            <div class="flex items-center gap-3 mb-4">
              <div class="size-10 rounded-xl bg-violet-50 dark:bg-violet-900/20 flex items-center justify-center">
                <Download :size="20" class="text-violet-500" />
              </div>
              <div>
                <h3 class="text-sm font-semibold">Install Skill</h3>
                <p class="text-xs text-[var(--text-tertiary)]">Install into the current ScienceClaw `Skills/` directory</p>
              </div>
            </div>

            <div class="space-y-4">
              <div>
                <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">Source</label>
                <input
                  v-model="installSource"
                  type="text"
                  placeholder="owner/repo@skill or https://skills.sh/owner/repo/skill"
                  class="w-full rounded-lg border border-[var(--border-light)] bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400/40"
                >
                <p class="mt-1.5 text-[11px] text-[var(--text-tertiary)]">
                  Examples: `davila7/claude-code-templates@literature-review`,
                  `https://skills.sh/kepano/obsidian-skills/obsidian-markdown`
                </p>
              </div>

              <div>
                <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">Skill Name (Optional)</label>
                <input
                  v-model="installSkillName"
                  type="text"
                  placeholder="Required only when the source repo contains multiple skills"
                  class="w-full rounded-lg border border-[var(--border-light)] bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400/40"
                >
              </div>

              <label class="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                <input v-model="installOverwrite" type="checkbox" class="rounded border-[var(--border-light)]">
                <span>Overwrite existing skill with the same name</span>
              </label>

              <div v-if="installError" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600 dark:border-red-900/40 dark:bg-red-900/10 dark:text-red-300">
                {{ installError }}
              </div>
            </div>

            <div class="flex justify-end gap-2 mt-6">
              <button @click="closeInstallModal" class="px-4 py-2 text-sm rounded-lg border border-[var(--border-light)] hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                {{ t('Cancel') }}
              </button>
              <button @click="executeInstall" :disabled="installing" class="px-4 py-2 text-sm rounded-lg bg-violet-500 text-white hover:bg-violet-600 disabled:opacity-50 transition-all">
                {{ installing ? 'Installing...' : 'Install' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <Transition name="modal">
        <div v-if="deleteTarget" class="fixed inset-0 z-[9999] flex items-center justify-center">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="cancelDelete"></div>
          <div class="relative bg-white dark:bg-[#2a2a2a] rounded-2xl shadow-2xl p-6 w-[380px] z-10">
            <div class="flex items-center gap-3 mb-4">
              <div class="size-10 rounded-xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
                <Trash2 :size="20" class="text-red-500" />
              </div>
              <div><h3 class="text-sm font-semibold">{{ t('Delete Skill') }}</h3><p class="text-xs text-[var(--text-tertiary)]">{{ t('This action cannot be undone') }}</p></div>
            </div>
            <p class="text-sm text-[var(--text-secondary)] mb-5">{{ t('Are you sure you want to delete "{name}"?', { name: deleteTarget.name }) }}</p>
            <div class="flex justify-end gap-2">
              <button @click="cancelDelete" class="px-4 py-2 text-sm rounded-lg border border-[var(--border-light)] hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">{{ t('Cancel') }}</button>
              <button @click="executeDelete" :disabled="deleting" class="px-4 py-2 text-sm rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 transition-all">
                {{ deleting ? t('Deleting...') : t('Delete') }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Search, Eye, EyeOff, Trash2, Box, Download } from 'lucide-vue-next';
import { getSkills, installSkill as apiInstallSkill, blockSkill, deleteSkill as apiDeleteSkill } from '../api/agent';
import { ExternalSkillItem } from '../types/response';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const router = useRouter();
const searchQuery = ref('');
const skills = ref<ExternalSkillItem[]>([]);
const loading = ref(false);
const installOpen = ref(false);
const installing = ref(false);
const installSource = ref('');
const installSkillName = ref('');
const installOverwrite = ref(false);
const installError = ref('');

const gradientPalette = [
  'linear-gradient(135deg, #8b5cf6, #a855f7)',
  'linear-gradient(135deg, #6366f1, #8b5cf6)',
  'linear-gradient(135deg, #ec4899, #f43f5e)',
  'linear-gradient(135deg, #d946ef, #ec4899)',
  'linear-gradient(135deg, #7c3aed, #6366f1)',
  'linear-gradient(135deg, #f43f5e, #f97316)',
  'linear-gradient(135deg, #a855f7, #ec4899)',
  'linear-gradient(135deg, #6366f1, #3b82f6)',
];

const getSkillGradient = (name: string) => {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return gradientPalette[Math.abs(hash) % gradientPalette.length];
};

const normalizeList = (value: unknown): string[] => {
  if (Array.isArray(value)) return value.map(item => String(item).trim()).filter(Boolean);
  if (typeof value === 'string') return value.split(',').map(item => item.trim()).filter(Boolean);
  return [];
};

const getMetadata = (skill: ExternalSkillItem): Record<string, any> => {
  return (skill.metadata && typeof skill.metadata === 'object') ? skill.metadata : {};
};

const getSkillBadges = (skill: ExternalSkillItem): string[] => {
  const metadata = getMetadata(skill);
  const badges = [
    ...normalizeList(metadata.research_tasks_zh),
    ...normalizeList(metadata.integrations).map(item => item === 'web-search' ? '联网发现' : item),
    ...normalizeList(metadata.output_modes_zh),
  ];
  return Array.from(new Set(badges)).slice(0, 8);
};

const getSkillFooter = (skill: ExternalSkillItem): string => {
  const metadata = getMetadata(skill);
  if (metadata.discovery_enabled) return 'Research router';
  if (normalizeList(metadata.integrations).includes('obsidian')) return 'Obsidian workflow';
  return 'Agent skill';
};

const getSearchableText = (skill: ExternalSkillItem): string => {
  const metadata = getMetadata(skill);
  return [
    skill.name,
    skill.description,
    JSON.stringify(metadata),
    ...(skill.files || []),
  ].join(' ').toLowerCase();
};

const openSkill = (skill: ExternalSkillItem) => { router.push(`/chat/skills/${skill.name}`); };

const loadSkills = async () => {
  loading.value = true;
  try { skills.value = await getSkills(); } catch (e) { console.error(e); }
  finally { loading.value = false; }
};

onMounted(loadSkills);

const filteredSkills = computed(() => {
  if (!searchQuery.value) return skills.value;
  const needle = searchQuery.value.toLowerCase().trim();
  return skills.value.filter(skill => getSearchableText(skill).includes(needle));
});

const handleToggleBlock = async (skill: ExternalSkillItem) => {
  try { await blockSkill(skill.name, !skill.blocked); skill.blocked = !skill.blocked; } catch (e) { console.error(e); }
};

const getApiErrorMessage = (error: unknown): string => {
  const maybe = error as { details?: { detail?: string }; message?: string };
  return maybe?.details?.detail || maybe?.message || 'Install failed';
};

const openInstallModal = () => {
  installError.value = '';
  installOpen.value = true;
};

const closeInstallModal = () => {
  if (!installing.value) installOpen.value = false;
};

const executeInstall = async () => {
  const source = installSource.value.trim();
  if (!source) {
    installError.value = 'Source is required.';
    return;
  }

  installing.value = true;
  installError.value = '';
  try {
    const result = await apiInstallSkill({
      source,
      skill_name: installSkillName.value.trim() || undefined,
      overwrite: installOverwrite.value,
    });
    await loadSkills();
    searchQuery.value = result.skill_name;
    installOpen.value = false;
    installSource.value = '';
    installSkillName.value = '';
    installOverwrite.value = false;
  } catch (error) {
    installError.value = getApiErrorMessage(error);
  } finally {
    installing.value = false;
  }
};

const deleteTarget = ref<ExternalSkillItem | null>(null);
const deleting = ref(false);
const confirmDeleteSkill = (skill: ExternalSkillItem) => { deleteTarget.value = skill; };
const cancelDelete = () => { if (!deleting.value) deleteTarget.value = null; };
const executeDelete = async () => {
  if (!deleteTarget.value) return; deleting.value = true;
  try { await apiDeleteSkill(deleteTarget.value.name); skills.value = skills.value.filter(s => s.name !== deleteTarget.value!.name); deleteTarget.value = null; }
  catch (e) { console.error(e); } finally { deleting.value = false; }
};
</script>

<style scoped>
.skill-card {
  animation: cardFadeIn 0.4s ease-out both;
  animation-delay: var(--delay, 0ms);
}
@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(12px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.skill-card:hover { transform: translateY(-2px); box-shadow: 0 12px 28px -8px rgba(0,0,0,0.08), 0 4px 12px -4px rgba(0,0,0,0.04); }

.modal-enter-active { transition: all 0.25s ease-out; }
.modal-leave-active { transition: all 0.2s ease-in; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from > div:last-child { transform: scale(0.95) translateY(10px); }
.modal-leave-to > div:last-child { transform: scale(0.95) translateY(10px); }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #e0e0e0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #ccc; }
</style>
