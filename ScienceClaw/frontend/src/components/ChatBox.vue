<template>
    <div class="pb-3 relative bg-[var(--background-gray-main)]">
        <!-- Optimization Panel — floats upward above the entire ChatBox -->
        <Transition name="opt-slide">
            <div v-if="showOptimization && optimizationResult"
                class="absolute bottom-full left-0 right-0 mb-2 z-30 px-1">
                <div class="bg-[var(--background-white-main)] rounded-2xl flex flex-col border border-[var(--border-main)] shadow-xl max-h-[50vh]">
                    <div class="flex items-center justify-between px-4 py-2.5 border-b border-[var(--border-light)]">
                        <div class="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
                            <Sparkles :size="14" class="text-purple-500" />
                            <span>{{ t('Optimized Prompt') }}</span>
                        </div>
                        <button @click="cancelOptimization" class="p-1 hover:bg-[var(--fill-tsp-gray-dark)] rounded-md transition-colors text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]">
                            <X :size="14" />
                        </button>
                    </div>
                    <div class="flex-1 overflow-y-auto p-4 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                        <template v-for="(chunk, idx) in optimizationResult.diff" :key="idx">
                            <span v-if="chunk.type === 'added'" class="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 rounded px-0.5 select-text">{{ chunk.value }}</span>
                            <span v-else-if="chunk.type === 'removed'" class="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 line-through opacity-60 rounded px-0.5 select-text">{{ chunk.value }}</span>
                            <span v-else class="text-[var(--text-primary)] select-text">{{ chunk.value }}</span>
                        </template>
                    </div>
                    <div class="flex justify-end gap-2 px-4 py-2.5 border-t border-[var(--border-light)]">
                        <button @click="cancelOptimization" class="px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] rounded-lg transition-colors">
                            {{ t('Cancel') }}
                        </button>
                        <button @click="applyOptimization" class="px-3 py-1.5 text-xs font-medium text-white bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:from-violet-600 hover:to-fuchsia-600 rounded-lg transition-all flex items-center gap-1 shadow-sm">
                            <CheckIcon :size="14" />
                            {{ t('Apply') }}
                        </button>
                    </div>
                </div>
            </div>
        </Transition>

        <div
            class="flex flex-col gap-3 rounded-[22px] transition-all duration-200 relative bg-[var(--fill-input-chat)] py-3 max-h-[400px] shadow-[0px_12px_32px_0px_rgba(0,0,0,0.02)] border border-black/8 dark:border-[var(--border-main)] focus-within:ring-2 focus-within:ring-indigo-500/15 focus-within:border-indigo-300/50 dark:focus-within:border-indigo-700/50">

            <ChatBoxFiles ref="chatBoxFileListRef" :attachments="attachments" :sessionId="sessionId"
                @files-changed="(f: any) => emit('files-changed', f)"
                @upload-ready="allFilesReady = $event" />

            <div class="overflow-y-auto pl-4 pr-2 relative min-h-[46px]">
                <textarea
                    ref="textarea"
                    class="flex rounded-md border-input focus-visible:outline-none focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 overflow-hidden flex-1 bg-transparent p-0 pt-[10px] border-0 focus-visible:ring-0 focus-visible:ring-offset-0 w-full placeholder:text-[var(--text-disable)] text-[15px] shadow-none resize-none min-h-[40px] max-h-[135px] overflow-y-auto"
                    :rows="rows"
                    v-model="input"
                    @compositionstart="isComposing = true" @compositionend="isComposing = false"
                    @keydown="handleKeydown"
                    :placeholder="t('Give ScienceClaw a task to work on...')"></textarea>
            </div>
            <footer class="flex flex-row justify-between w-full px-3">
                <div class="flex gap-2 pr-2 items-center">
                    <button @click="uploadFile"
                        class="rounded-full border border-[var(--border-main)] inline-flex items-center justify-center gap-1 clickable cursor-pointer text-xs text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] w-8 h-8 p-0 data-[popover-trigger]:bg-[var(--fill-tsp-gray-main)] shrink-0"
                        aria-expanded="false" aria-haspopup="dialog">
                        <Paperclip :size="16" />
                    </button>

                    <!-- ScienceClaw + Skills Management Popover -->
                    <Popover v-model:open="isPanelOpen">
                        <PopoverTrigger as-child>
                            <div class="flex items-center gap-2 bg-[var(--background-white-main)] rounded-full px-3 py-1 border border-[var(--border-light)] cursor-pointer hover:border-[var(--border-main)] transition-colors h-8">
                                <RobotAvatar class="w-4 h-4" />
                                <span class="text-xs font-medium text-[var(--text-secondary)]">ScienceClaw</span>
                            </div>
                        </PopoverTrigger>
                        <PopoverContent class="w-[320px] p-0 overflow-hidden bg-[var(--background-white-main)] border border-[var(--border-light)] shadow-xl rounded-xl" align="start" :side-offset="8">
                            
                            <div class="flex flex-col max-h-[420px] overflow-y-auto p-1.5">
                                <!-- DEFAULT Section -->
                                <div class="mb-2">
                                    <div class="px-2 py-1.5 text-[10px] font-bold text-[var(--text-tertiary)] uppercase tracking-wider">Default</div>
                                    <div class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[var(--fill-tsp-gray-main)] border border-[var(--border-light)]">
                                        <div class="flex items-center justify-center w-9 h-9 rounded-full bg-[var(--background-gray-main)] border border-[var(--border-light)] flex-shrink-0 shadow-sm">
                                            <RobotAvatar class="w-5 h-5" :interactive="false" />
                                        </div>
                                        <div class="flex flex-col overflow-hidden flex-1">
                                            <span class="text-sm font-semibold text-[var(--text-primary)]">ScienceClaw</span>
                                            <span class="text-[11px] text-[var(--text-tertiary)]">General Purpose Assistant</span>
                                        </div>
                                        <div class="w-5 h-5 rounded-full bg-[var(--text-primary)] flex items-center justify-center shadow-sm">
                                            <Check :size="12" class="text-[var(--text-onblack)]" />
                                        </div>
                                    </div>
                                </div>

                                <!-- SKILLS Management Section -->
                                <div>
                                    <div class="px-2 py-1.5 text-[10px] font-bold text-[var(--text-tertiary)] uppercase tracking-wider flex justify-between items-center">
                                        <span>Skills</span>
                                        <span class="text-[9px] font-normal bg-[var(--background-gray-main)] px-1.5 py-0.5 rounded text-[var(--text-tertiary)]">{{ externalSkills.length }}</span>
                                    </div>

                                    <!-- Loading State -->
                                    <div v-if="loadingSkills" class="px-3 py-4 text-xs text-[var(--text-tertiary)] text-center flex flex-col items-center gap-2">
                                        <div class="w-4 h-4 border-2 border-[var(--border-main)] border-t-[var(--text-primary)] rounded-full animate-spin"></div>
                                        {{ t('Loading skills...') }}
                                    </div>
                                    
                                    <!-- Empty State -->
                                    <div v-else-if="externalSkills.length === 0" class="px-3 py-6 text-xs text-[var(--text-tertiary)] text-center flex flex-col items-center gap-2">
                                        <Box :size="24" class="opacity-20" />
                                        <span>{{ t('No external skills installed') }}</span>
                                    </div>

                                    <!-- Skills List -->
                                    <div v-else class="flex flex-col gap-0.5">
                                        <div 
                                            v-for="skill in externalSkills" 
                                            :key="skill.name"
                                            class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[var(--fill-tsp-gray-main)] transition-all group border border-transparent hover:border-[var(--border-light)]"
                                            :class="{ 'opacity-50': skill.blocked }"
                                        >
                                            <div class="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--background-gray-main)] border border-[var(--border-light)] text-[var(--text-secondary)] flex-shrink-0 shadow-sm">
                                                <Wrench :size="14" />
                                            </div>
                                            <div class="flex flex-col overflow-hidden flex-1 min-w-0">
                                                <span class="text-sm font-medium text-[var(--text-primary)] truncate">{{ skill.name }}</span>
                                                <span v-if="skill.description" class="text-[10px] text-[var(--text-tertiary)] truncate">{{ skill.description }}</span>
                                            </div>
                                            <div class="flex items-center gap-1 flex-shrink-0">
                                                <span v-if="skill.builtin" class="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-500 font-medium">Built-in</span>
                                                <template v-else>
                                                    <button 
                                                        @click.stop="handleToggleBlock(skill)"
                                                        class="p-1.5 rounded-md transition-colors"
                                                        :class="skill.blocked 
                                                            ? 'text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20' 
                                                            : 'text-[var(--text-tertiary)] hover:bg-[var(--fill-tsp-gray-main)] hover:text-[var(--text-secondary)]'"
                                                        :title="skill.blocked ? t('Unblock skill') : t('Block skill')"
                                                    >
                                                        <EyeOff v-if="skill.blocked" :size="14" />
                                                        <Eye v-else :size="14" />
                                                    </button>
                                                    <button 
                                                        @click.stop="confirmDeleteSkill(skill)"
                                                        class="p-1.5 rounded-md text-[var(--text-tertiary)] hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 transition-colors"
                                                        :title="t('Delete skill')"
                                                    >
                                                        <Trash2 :size="14" />
                                                    </button>
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </PopoverContent>
                    </Popover>

                    <!-- Model Selection -->
                    <div v-if="!currentModel" @click="emit('open-model-settings')"
                        class="flex items-center gap-2 bg-[var(--background-white-main)] rounded-full px-3 py-1 border border-[var(--border-light)] cursor-pointer hover:border-[var(--border-main)] transition-colors h-8 ml-2">
                        <span class="text-xs font-medium text-[var(--text-secondary)]">{{ currentModelName }}</span>
                    </div>
                    <Popover v-else v-model:open="isModelsOpen">
                        <PopoverTrigger as-child>
                             <div class="flex items-center gap-2 bg-[var(--background-white-main)] rounded-full px-3 py-1 border border-[var(--border-light)] cursor-pointer hover:border-[var(--border-main)] transition-colors h-8 ml-2">
                                <span class="text-xs font-medium text-[var(--text-secondary)] flex items-center gap-1">
                                    <ProviderIcon :provider="currentModel.provider" class="size-4 mr-1" />
                                    {{ currentModelName }}
                                </span>
                            </div>
                        </PopoverTrigger>
                        <PopoverContent class="w-[280px] p-0 overflow-hidden" align="start" :side-offset="8">
                            <div class="bg-[var(--background-gray-main)] px-3 py-2 border-b border-[var(--border-light)]">
                                <span class="text-xs font-medium text-[var(--text-tertiary)]">Select Model</span>
                            </div>
                            <div class="flex flex-col max-h-[300px] overflow-y-auto p-1">
                                <button 
                                    v-for="model in models" 
                                    :key="model.id"
                                    @click="selectModel(model.id)"
                                    class="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[var(--fill-tsp-gray-main)] transition-all text-left group"
                                    :class="{'bg-[var(--fill-tsp-gray-main)]': selectedModelId === model.id}"
                                >
                                    <div class="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--background-gray-main)] border border-[var(--border-light)] text-[var(--text-secondary)] group-hover:border-[var(--border-main)] transition-colors flex-shrink-0">
                                        <ProviderIcon :provider="model.provider" class="size-4" />
                                    </div>
                                    <div class="flex flex-col overflow-hidden flex-1">
                                        <span class="text-sm font-medium text-[var(--text-primary)] truncate">
                                            {{ model.name.toLowerCase() === 'system' ? model.model_name : model.name }}
                                        </span>
                                        <span class="text-[10px] text-[var(--text-tertiary)] truncate">{{ model.provider }}</span>
                                    </div>
                                    <Check v-if="selectedModelId === model.id" :size="16" class="text-[var(--text-primary)] flex-shrink-0" />
                                </button>
                            </div>
                        </PopoverContent>
                    </Popover>
                </div>
                <div class="flex gap-2 items-center">
                    <button
                        @click="handleCopyInput"
                        :disabled="!canCopyInput"
                        class="p-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors hover:bg-[var(--fill-tsp-gray-main)] disabled:opacity-30 disabled:cursor-not-allowed"
                        :class="inputCopied ? 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'"
                        :title="inputCopied ? t('Input Copied') : t('Copy Input')"
                        :aria-label="inputCopied ? t('Input Copied') : t('Copy Input')">
                        <Check v-if="inputCopied" :size="16" />
                        <Copy v-else :size="16" />
                    </button>

                    <button 
                        @click="handleOptimize"
                        :disabled="!hasTextInput || isOptimizing || showOptimization"
                        class="mr-2 p-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors hover:bg-[var(--fill-tsp-gray-main)] disabled:opacity-30 disabled:cursor-not-allowed"
                        :class="isOptimizing ? 'cursor-default text-purple-500' : 'cursor-pointer text-purple-500 hover:text-purple-600'"
                        title="Optimize Prompt">
                        <RefreshCw v-if="isOptimizing" :size="16" class="animate-spin" />
                        <Sparkles v-else :size="18" />
                    </button>

                    <button v-if="!isRunning"
                        class="whitespace-nowrap text-sm font-medium focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 text-primary-foreground hover:bg-primary/90 p-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors hover:opacity-90"
                        :class="!sendEnabled ? 'cursor-not-allowed bg-gray-300 dark:bg-gray-700' : 'cursor-pointer bg-gradient-to-r from-blue-500 to-indigo-600 hover:shadow-lg hover:shadow-indigo-500/25 active:scale-95'"
                        @click="handleSubmit">
                        <SendIcon :disabled="!sendEnabled" />
                    </button>
                    <button v-else @click="handleStop"
                        class="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring bg-red-600 hover:bg-red-700 text-white gap-[4px] rounded-full p-0 w-8 h-8"
                        :title="t('Stop task')">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5">
                            <rect x="6" y="6" width="12" height="12" rx="2" />
                        </svg>
                    </button>
                </div>
            </footer>
        </div>

        <!-- Delete Skill Confirmation Dialog -->
        <Teleport to="body">
            <div v-if="deleteTarget" class="fixed inset-0 z-[9999] flex items-center justify-center">
                <div class="absolute inset-0 bg-black/40" @click="cancelDelete"></div>
                <div class="relative bg-[var(--background-white-main)] rounded-xl shadow-2xl border border-[var(--border-light)] w-[360px] max-w-[90vw] animate-in fade-in zoom-in-95 duration-200">
                    <button 
                        @click="cancelDelete"
                        class="absolute top-3 right-3 p-1 rounded-md text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--fill-tsp-gray-main)] transition-colors"
                    >
                        <X :size="16" />
                    </button>
                    <div class="p-6">
                        <div class="flex items-center gap-3 mb-4">
                            <div class="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
                                <Trash2 :size="20" class="text-red-500" />
                            </div>
                            <div>
                                <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('Delete Skill') }}</h3>
                            </div>
                        </div>
                        <p class="text-sm text-[var(--text-secondary)] mb-6">
                            {{ t('Are you sure you want to delete the skill "{name}"?', { name: deleteTarget.name }) }}
                        </p>
                        <div class="flex justify-end gap-2">
                            <button 
                                @click="cancelDelete"
                                class="px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] rounded-lg transition-colors"
                            >
                                {{ t('Cancel') }}
                            </button>
                            <button 
                                @click="executeDelete"
                                :disabled="deleting"
                                class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1.5"
                            >
                                <div v-if="deleting" class="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin"></div>
                                {{ t('Confirm') }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </Teleport>
    </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from 'vue';
import SendIcon from './icons/SendIcon.vue';
import { useI18n } from 'vue-i18n';
import ChatBoxFiles from './ChatBoxFiles.vue';
import { Paperclip, Wrench, Check, Box, Eye, EyeOff, Trash2, Sparkles, X, Check as CheckIcon, RefreshCw, Copy } from 'lucide-vue-next';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import RobotAvatar from './icons/RobotAvatar.vue';
import ProviderIcon from './icons/ProviderIcon.vue';
import type { FileInfo } from '../api/file';
import type { ModelConfig } from '../api/models';
import type { ExternalSkillItem } from '../types/response';
import { optimizePrompt, getSkills, blockSkill, deleteSkill as apiDeleteSkill } from '../api/agent';
import { useTextareaAutosize } from '@vueuse/core';
import { copyToClipboard } from '../utils/dom';
import { showErrorToast, showSuccessToast } from '../utils/toast';

const props = defineProps<{
    modelValue: string;
    rows: number;
    isRunning: boolean;
    attachments: FileInfo[];
    sessionId?: string;
    models?: ModelConfig[];
    selectedModelId?: string | null;
}>();

const emit = defineEmits<{
    (e: 'update:modelValue', value: string): void;
    (e: 'submit'): void;
    (e: 'stop'): void;
    (e: 'update:selectedModelId', value: string): void;
    (e: 'files-changed', files: any[]): void;
    (e: 'upload-ready', ready: boolean): void;
    (e: 'open-model-settings'): void;
}>();

const { t } = useI18n();
const { textarea, input } = useTextareaAutosize();

watch(() => props.modelValue, (newVal) => {
    if (newVal !== input.value) {
        input.value = newVal;
    }
}, { immediate: true });

watch(input, (newVal) => {
    emit('update:modelValue', newVal);
});

const hasTextInput = ref(false);
const isComposing = ref(false);
const chatBoxFileListRef = ref();
const allFilesReady = ref(true);
const isPanelOpen = ref(false);
const isModelsOpen = ref(false);

const isOptimizing = ref(false);
const showOptimization = ref(false);
const optimizationResult = ref<{ original: string; optimized: string; diff: { type: 'same' | 'added' | 'removed'; value: string }[] } | null>(null);
const inputCopied = ref(false);
let inputCopyTimer: ReturnType<typeof setTimeout> | null = null;

watch(input, (value) => {
    hasTextInput.value = value.trim() !== '';
}, { immediate: true });

const canCopyInput = computed(() => input.value.length > 0);

const clearInputCopyTimer = () => {
    if (inputCopyTimer) {
        clearTimeout(inputCopyTimer);
        inputCopyTimer = null;
    }
};

const showInputCopiedState = () => {
    clearInputCopyTimer();
    inputCopied.value = true;
    inputCopyTimer = setTimeout(() => {
        inputCopied.value = false;
        inputCopyTimer = null;
    }, 2000);
};

onUnmounted(() => {
    clearInputCopyTimer();
});

// ── Skills Management ──
const externalSkills = ref<ExternalSkillItem[]>([]);
const loadingSkills = ref(false);

const loadExternalSkills = async () => {
    loadingSkills.value = true;
    try {
        externalSkills.value = await getSkills();
    } catch (e) {
        console.error("Failed to load skills", e);
        externalSkills.value = [];
    } finally {
        loadingSkills.value = false;
    }
};

watch(isPanelOpen, (open) => {
    if (open) loadExternalSkills();
});

onMounted(() => {
    loadExternalSkills();
});

const handleToggleBlock = async (skill: ExternalSkillItem) => {
    const newBlocked = !skill.blocked;
    try {
        await blockSkill(skill.name, newBlocked);
        skill.blocked = newBlocked;
    } catch (e) {
        console.error("Failed to toggle block", e);
    }
};

// ── Delete Confirmation ──
const deleteTarget = ref<ExternalSkillItem | null>(null);
const deleting = ref(false);

const confirmDeleteSkill = (skill: ExternalSkillItem) => {
    deleteTarget.value = skill;
};

const cancelDelete = () => {
    if (!deleting.value) {
        deleteTarget.value = null;
    }
};

const executeDelete = async () => {
    if (!deleteTarget.value) return;
    deleting.value = true;
    try {
        await apiDeleteSkill(deleteTarget.value.name);
        externalSkills.value = externalSkills.value.filter(s => s.name !== deleteTarget.value!.name);
        deleteTarget.value = null;
    } catch (e) {
        console.error("Failed to delete skill", e);
    } finally {
        deleting.value = false;
    }
};

// ── Model Selection ──
const currentModel = computed(() => {
    if (!props.models || props.models.length === 0) return null;
    if (!props.selectedModelId) {
        return props.models.find(m => m.is_system) || props.models[0];
    }
    return props.models.find(m => m.id === props.selectedModelId) || null;
});

const currentModelName = computed(() => {
    const model = currentModel.value;
    if (!model) return t('Select Model');
    return model.name;
});

const selectModel = (id: string) => {
    emit('update:selectedModelId', id);
    isModelsOpen.value = false;
};

// ── Submit / Stop ──
const sendEnabled = computed(() => {
    return allFilesReady.value && hasTextInput.value;
});

const handleKeydown = (event: KeyboardEvent) => {
    if (isComposing.value) return;
    if (event.key === 'Enter' && !event.shiftKey) {
        if (sendEnabled.value) {
            event.preventDefault();
            handleSubmit();
        } else {
            event.preventDefault();
        }
    }
};

const handleSubmit = () => {
    if (!sendEnabled.value) return;
    emit('submit');
};

const handleCopyInput = async () => {
    if (!canCopyInput.value) return;

    try {
        const success = await copyToClipboard(input.value);
        if (success) {
            showInputCopiedState();
            showSuccessToast(t('Input copied to clipboard'));
            return;
        }
    } catch (error) {
        console.error('Failed to copy input', error);
    }

    inputCopied.value = false;
    clearInputCopyTimer();
    showErrorToast(t('Failed to copy input'));
};

const handleStop = () => {
    emit('stop');
};

const uploadFile = () => {
    chatBoxFileListRef.value?.uploadFile();
};

// ── Prompt Optimization ──
const handleOptimize = async () => {
    if (!hasTextInput.value || isOptimizing.value) return;
    const originalText = props.modelValue;
    isOptimizing.value = true;
    try {
        const result = await optimizePrompt(originalText, props.selectedModelId);
        const optimizedText = result.optimized_query;
        const diff = computeDiff(originalText, optimizedText);
        optimizationResult.value = { original: originalText, optimized: optimizedText, diff };
        showOptimization.value = true;
    } catch (e) {
        console.error("Optimization failed", e);
    } finally {
        isOptimizing.value = false;
    }
};

const cancelOptimization = () => {
    showOptimization.value = false;
    optimizationResult.value = null;
};

const applyOptimization = () => {
    if (optimizationResult.value) {
        emit('update:modelValue', optimizationResult.value.optimized);
    }
    cancelOptimization();
};

const computeDiff = (text1: string, text2: string) => {
    const tokenize = (text: string) => text.split('');
    const words1 = tokenize(text1);
    const words2 = tokenize(text2);
    const n = words1.length;
    const m = words2.length;
    const dp = Array(n + 1).fill(0).map(() => Array(m + 1).fill(0));
    for (let i = 1; i <= n; i++) {
        for (let j = 1; j <= m; j++) {
            if (words1[i-1] === words2[j-1]) {
                dp[i][j] = dp[i-1][j-1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i-1][j], dp[i][j-1]);
            }
        }
    }
    const diff = [];
    let i = n, j = m;
    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && words1[i-1] === words2[j-1]) {
            diff.unshift({ type: 'same', value: words1[i-1] });
            i--; j--;
        } else if (j > 0 && (i === 0 || dp[i][j-1] >= dp[i-1][j])) {
            diff.unshift({ type: 'added', value: words2[j-1] });
            j--;
        } else {
            diff.unshift({ type: 'removed', value: words1[i-1] });
            i--;
        }
    }
    if (diff.length === 0) return [];
    const mergedDiff = [];
    let current = diff[0];
    for (let k = 1; k < diff.length; k++) {
        if (diff[k].type === current.type) {
            current.value += diff[k].value;
        } else {
            mergedDiff.push(current);
            current = diff[k];
        }
    }
    mergedDiff.push(current);
    return mergedDiff as { type: 'same' | 'added' | 'removed'; value: string }[];
};

const uploadPendingFiles = async (sessionId: string) => {
    return chatBoxFileListRef.value?.uploadPendingFiles(sessionId) ?? [];
};

const getFiles = () => {
    return chatBoxFileListRef.value?.getFiles() ?? [];
};

const hasFiles = computed(() => {
    return chatBoxFileListRef.value?.hasFiles ?? false;
});

defineExpose({
    uploadPendingFiles,
    getFiles,
    hasFiles
});
</script>

<style scoped>
.opt-slide-enter-active,
.opt-slide-leave-active {
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.opt-slide-enter-from,
.opt-slide-leave-to {
    opacity: 0;
    transform: translateY(12px);
}
</style>
