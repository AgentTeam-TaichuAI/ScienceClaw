<template>
  <div class="flex flex-col gap-6 py-2 px-1">
    <div v-if="loading" class="flex justify-center py-12">
      <Loader2 class="size-8 animate-spin text-gray-300" />
    </div>

    <div v-else class="flex flex-col gap-8">
      <!-- Free Token Banner -->
      <div class="relative overflow-hidden rounded-2xl border border-indigo-200 dark:border-indigo-800/50 bg-gradient-to-br from-indigo-50 via-blue-50 to-purple-50 dark:from-indigo-950/40 dark:via-blue-950/30 dark:to-purple-950/30 p-6">
        <div class="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-indigo-200/40 to-transparent rounded-bl-full"></div>
        <div class="relative flex flex-col gap-4">
          <div class="flex items-start gap-4">
            <div class="size-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30 flex-shrink-0">
              <Gift class="size-6" />
            </div>
            <div class="flex flex-col gap-1">
              <h3 class="text-lg font-bold text-gray-800 dark:text-gray-100">{{ t('Get Started for Free') }}</h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                {{ t('No API key yet? Get 10 million free tokens to start exploring — no credit card required.') }}
              </p>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-3 ml-16">
            <a
              href="https://www.scnet.cn/ui/mall/en"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-cyan-600 rounded-xl shadow-md shadow-blue-500/25 hover:shadow-lg hover:shadow-blue-500/40 active:scale-[0.97] transition-all duration-200"
            >
              <Sparkles class="size-4" />
              {{ t('SCNet · 10M Tokens') }}
              <ExternalLink class="size-3.5 opacity-70" />
            </a>
            <a
              href="https://gateway.taichuai.cn/modelhub/apply"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl shadow-md shadow-indigo-500/25 hover:shadow-lg hover:shadow-indigo-500/40 active:scale-[0.97] transition-all duration-200"
            >
              <Sparkles class="size-4" />
              {{ t('Taichu Cloud · 10M Tokens') }}
              <ExternalLink class="size-3.5 opacity-70" />
            </a>
          </div>
        </div>
      </div>

      <!-- System Models Section -->
      <div v-if="systemModels.length > 0" class="flex flex-col gap-4">
        <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-1 flex items-center gap-2">
            {{ t('System Models') }}
            <span class="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent"></span>
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
            v-for="model in systemModels"
            :key="model.id"
            class="group relative flex flex-col bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm hover:border-blue-200 dark:hover:border-blue-700/50 hover:shadow-md transition-all duration-300 overflow-hidden"
            >
                <!-- Header with Status -->
                <div class="absolute top-0 right-0 p-3">
                    <div class="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-full border border-emerald-100 dark:border-emerald-800/40 shadow-sm">
                        <CheckCircle2 class="size-3.5" />
                        <span class="text-[10px] font-bold uppercase tracking-wide">{{ t('Verified') }}</span>
                    </div>
                </div>

                <!-- Main Content -->
                <div class="p-5 flex flex-col gap-4">
                    <!-- Title Area -->
                    <div class="flex items-start gap-4">
                        <div class="size-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
                            <ShieldCheck class="size-6" />
                        </div>
                        <div class="flex flex-col pt-0.5">
                            <h4 class="font-bold text-gray-800 dark:text-gray-100 text-lg leading-tight">{{ model.name }}</h4>
                            <span class="text-xs font-medium text-gray-400 dark:text-gray-500 mt-1">
                                {{ t('System Built-in') }}
                            </span>
                        </div>
                    </div>

                    <!-- Info Grid -->
                    <div class="grid grid-cols-1 gap-2 bg-[var(--background-gray-main)] rounded-lg p-3 border border-[var(--border-light)]">
                        <!-- Provider -->
                        <div class="flex items-center justify-between text-xs">
                            <span class="text-[var(--text-tertiary)] flex items-center gap-1.5 whitespace-nowrap">
                                <Box class="size-3.5" />
                                {{ t('Provider') }}
                            </span>
                            <span class="font-semibold text-[var(--text-secondary)] capitalize">{{ model.provider }}</span>
                        </div>
                        
                        <!-- Model ID -->
                        <div class="flex items-center justify-between text-xs border-t border-[var(--border-light)] border-dashed pt-2">
                            <span class="text-[var(--text-tertiary)] flex items-center gap-1.5 whitespace-nowrap">
                                <Box class="size-3.5" />
                                {{ t('Model ID') }}
                            </span>
                            <span class="font-mono text-[var(--text-primary)] bg-white px-1.5 rounded border border-[var(--border-light)]">{{ model.model_name }}</span>
                        </div>

                        <!-- Base URL -->
                        <div class="flex items-center justify-between text-xs border-t border-[var(--border-light)] border-dashed pt-2">
                            <span class="text-[var(--text-tertiary)] flex items-center gap-1.5 whitespace-nowrap">
                                <Globe class="size-3.5" />
                                {{ t('Base URL') }}
                            </span>
                            <div class="flex-1 flex justify-end ml-4 overflow-hidden">
                                <span v-if="!model.base_url" class="px-1.5 py-0.5 rounded bg-gray-100 text-[var(--text-tertiary)] text-[10px] font-medium border border-[var(--border-light)] whitespace-nowrap">
                                    {{ t('Default Endpoint') }}
                                </span>
                                <span v-else class="font-mono text-[var(--text-tertiary)] truncate" :title="model.base_url">
                                    {{ model.base_url }}
                                </span>
                            </div>
                        </div>

                         <!-- API Key -->
                        <div class="flex items-center justify-between text-xs border-t border-[var(--border-light)] border-dashed pt-2">
                            <span class="text-[var(--text-tertiary)] flex items-center gap-1.5 whitespace-nowrap">
                                <Key class="size-3.5" />
                                {{ t('API Key') }}
                            </span>
                            <div class="flex items-center gap-1.5">
                                <span class="size-2 rounded-full bg-green-500 animate-pulse"></span>
                                <span class="font-mono text-[var(--text-tertiary)] text-[10px]">********</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      </div>

      <!-- User Models Section -->
      <div class="flex flex-col gap-4">
        <div class="flex justify-between items-center px-1">
             <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider flex items-center gap-2 flex-1">
                {{ t('Custom Models') }}
                <span class="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent mr-4"></span>
             </h3>
             <button
                class="flex items-center gap-1.5 px-4 py-2 text-white bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl text-xs font-semibold shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.97] transition-all duration-200 group"
                @click="openEditModal(null)"
            >
                <Plus class="size-3.5" />
                {{ t('Add Model') }}
            </button>
        </div>

        <div v-if="userModels.length === 0" class="flex flex-col items-center justify-center py-12 bg-gray-50/80 dark:bg-gray-800/30 rounded-2xl border-2 border-dashed border-gray-200 dark:border-gray-700">
            <div class="size-14 rounded-2xl bg-gradient-to-br from-gray-100 to-gray-50 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center mb-3">
                <Box class="size-6 text-gray-300 dark:text-gray-500" />
            </div>
            <p class="font-semibold text-gray-400 dark:text-gray-500">{{ t('No custom models configured') }}</p>
            <p class="text-xs mt-1 text-gray-300 dark:text-gray-600">{{ t('Add your own OpenAI, Anthropic or other compatible models.') }}</p>
        </div>
        
        <div v-else class="grid grid-cols-1 gap-3">
             <div 
                v-for="model in userModels" 
                :key="model.id"
                class="group flex items-center justify-between p-4 bg-[var(--background-white-main)] border border-[var(--border-light)] rounded-xl hover:border-[var(--border-main)] hover:shadow-md transition-all duration-200"
            >
                <div class="flex flex-col gap-1.5">
                    <div class="flex items-center gap-3">
                        <div class="size-8 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-500">
                             <Box class="size-4" />
                        </div>
                        <div class="flex flex-col">
                            <span class="font-semibold text-[var(--text-primary)] text-sm">{{ model.name }}</span>
                            <div class="flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
                                <span class="capitalize">{{ model.provider }}</span>
                                <span class="text-[var(--text-disable)]">•</span>
                                <span class="font-mono">{{ model.model_name }}</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <button 
                        class="p-2 text-[var(--text-secondary)] hover:text-[var(--icon-primary)] hover:bg-[var(--background-gray-main)] rounded-lg transition-all"
                        :title="t('Edit')"
                        @click="openEditModal(model)"
                    >
                        <Pencil class="size-4" />
                    </button>
                    <button 
                        class="p-2 text-[var(--text-secondary)] hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                        :title="t('Delete')"
                        @click="confirmDelete(model)"
                    >
                        <Trash2 class="size-4" />
                    </button>
                </div>
            </div>
        </div>
      </div>
    </div>

    <!-- Edit/Add Dialog -->
    <Dialog v-model:open="isEditOpen">
      <DialogContent class="sm:max-w-[780px] p-0 flex flex-col max-h-[85vh] bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-gray-200/60 dark:border-gray-700/40">
        <DialogHeader class="px-6 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 flex flex-row items-center justify-between flex-shrink-0">
          <DialogTitle class="text-lg font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
            <div class="size-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <Box class="size-4 text-white" />
            </div>
            {{ editingModel ? t('Edit Model') : t('Add Model') }}
          </DialogTitle>
        </DialogHeader>
        
        <div class="px-6 py-6 flex flex-col gap-5 flex-1 overflow-y-auto min-h-0">
            <!-- Provider Selection -->
             <div class="grid gap-2">
                <label class="text-sm font-medium text-[var(--text-secondary)]">{{ t('Provider') }} <span class="text-red-500">*</span></label>
                <div class="grid grid-cols-3 gap-2">
                    <button 
                        v-for="p in ['openai', 'anthropic', 'deepseek', 'gemini', 'glm', 'qwen', 'kimi', 'minimax', 'taichu', 'other']" 
                        :key="p"
                        type="button"
                        class="px-3 py-2 rounded-lg text-xs font-medium border transition-all capitalize flex items-center justify-center gap-1.5"
                        :class="form.provider === p ? 'bg-blue-50 border-blue-200 text-blue-700 ring-1 ring-blue-200' : 'bg-[var(--background-white-main)] border-[var(--border-main)] text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)]'"
                        @click="selectProvider(p)"
                    >
                        <ProviderIcon :provider="p" class="size-4" />
                        {{ p }}
                    </button>
                </div>
            </div>

            <!-- Display Name & Model Name -->
            <div class="grid grid-cols-[2fr_3fr] gap-4">
                 <div class="grid gap-2">
                    <label class="text-sm font-medium text-[var(--text-secondary)]">{{ t('Display Name') }} <span class="text-red-500">*</span></label>
                    <input 
                    v-model="form.name" 
                    class="flex h-9 w-full rounded-md border border-[var(--border-main)] bg-[var(--fill-input-chat)] px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--text-disable)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-dark)] disabled:cursor-not-allowed disabled:opacity-50"
                    placeholder="e.g. My GPT-4"
                    />
                </div>
                <div class="grid gap-2">
                    <label class="text-sm font-medium text-[var(--text-secondary)]">{{ t('Model ID') }} <span class="text-red-500">*</span></label>
                    <div v-if="form.provider !== 'other' && providerModels.length > 0" class="relative" ref="dropdownRef">
                        <button
                            type="button"
                            class="flex h-9 w-full items-center justify-between rounded-md border border-[var(--border-main)] bg-[var(--fill-input-chat)] px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-dark)]"
                            @click="modelDropdownOpen = !modelDropdownOpen"
                        >
                            <span :class="form.model_name ? 'text-[var(--text-primary)]' : 'text-[var(--text-disable)]'">
                                {{ form.model_name || t('Select a model') }}
                            </span>
                            <ChevronDown class="size-4 text-gray-400 shrink-0 transition-transform" :class="modelDropdownOpen && 'rotate-180'" />
                        </button>
                        <div v-if="modelDropdownOpen" class="absolute z-50 mt-1 w-full rounded-lg border border-[var(--border-main)] bg-white dark:bg-gray-800 shadow-lg overflow-hidden">
                            <div class="max-h-48 overflow-y-auto py-1">
                                <button
                                    v-for="m in providerModels"
                                    :key="m"
                                    type="button"
                                    class="flex w-full items-center px-3 py-2 text-sm hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
                                    :class="form.model_name === m ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium' : 'text-[var(--text-primary)]'"
                                    @click="selectModel(m)"
                                >
                                    {{ m }}
                                </button>
                            </div>
                            <div class="border-t border-[var(--border-light)] p-2">
                                <input
                                    v-model="customModelInput"
                                    class="flex h-8 w-full rounded-md border border-[var(--border-main)] bg-[var(--fill-input-chat)] px-2 py-1 text-xs shadow-sm placeholder:text-[var(--text-disable)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-dark)]"
                                    :placeholder="t('Enter other model')"
                                    @keydown.enter.prevent="applyCustomModel"
                                />
                            </div>
                        </div>
                    </div>
                    <input
                    v-else
                    v-model="form.model_name"
                    @input="onModelSelect"
                    class="flex h-9 w-full rounded-md border border-[var(--border-main)] bg-[var(--fill-input-chat)] px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--text-disable)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-dark)] disabled:cursor-not-allowed disabled:opacity-50"
                    placeholder="e.g. gpt-4-turbo"
                    />
                </div>
            </div>

            <!-- Base URL (hidden for Gemini — uses Google AI SDK directly) -->
            <div v-if="form.provider !== 'gemini'" class="grid gap-2">
                <label class="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1">
                    {{ t('Base URL') }}
                    <span class="text-[10px] text-[var(--text-tertiary)] font-normal ml-auto" v-if="!form.base_url && form.provider !== 'other'">{{ t('Please fill in manually') }}</span>
                </label>
                <input 
                v-model="form.base_url" 
                class="flex h-9 w-full rounded-md border border-[var(--border-main)] bg-[var(--fill-input-chat)] px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--text-disable)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-dark)] disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="https://api.openai.com/v1"
                />
            </div>

            <!-- API Key -->
            <div class="grid gap-2">
                <label class="text-sm font-medium text-[var(--text-secondary)]">{{ t('API Key') }} <span class="text-red-500" v-if="!editingModel">*</span></label>
                <input 
                v-model="form.api_key" 
                type="password"
                class="flex h-9 w-full rounded-md border border-[var(--border-main)] bg-[var(--fill-input-chat)] px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--text-disable)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-dark)] disabled:cursor-not-allowed disabled:opacity-50 font-mono"
                :placeholder="editingModel ? t('Leave empty to keep existing key') : 'sk-...'"
                />
            </div>

            <!-- Context Window -->
            <div class="grid gap-2">
                <label class="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1">
                    {{ t('Context Window') }}
                    <span class="text-[10px] text-[var(--text-tertiary)] font-normal ml-auto">{{ t('Auto-detected if empty') }}</span>
                </label>
                <div class="flex gap-2">
                    <input 
                    v-model.number="form.context_window" 
                    type="number"
                    min="1024"
                    step="1024"
                    class="flex h-9 w-full rounded-md border border-[var(--border-main)] bg-[var(--fill-input-chat)] px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--text-disable)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-dark)] disabled:cursor-not-allowed disabled:opacity-50 font-mono"
                    :placeholder="t('e.g. 131072')"
                    />
                    <button
                        type="button"
                        :disabled="detecting || !form.model_name"
                        @click="detectCtxWindow"
                        class="flex-shrink-0 h-9 px-3 rounded-md border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 text-xs font-medium hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                        :title="t('Detect')"
                    >
                        <Loader2 v-if="detecting" class="size-3.5 animate-spin" />
                        <Radar v-else class="size-3.5" />
                        {{ t('Detect') }}
                    </button>
                </div>
            </div>
        </div>

        <DialogFooter class="px-6 py-4 bg-gray-50/50 dark:bg-gray-800/30 border-t border-gray-100 dark:border-gray-800 flex justify-between items-center flex-shrink-0">
          <div class="text-xs text-gray-400" v-if="saving">{{ t('Verifying connection...') }}</div>
          <div class="flex gap-3 ml-auto">
            <button
                class="px-5 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-600 transition-all shadow-sm"
                @click="isEditOpen = false"
            >
                {{ t('Cancel') }}
            </button>
            <button
                class="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.97] transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="saving"
                @click="saveModel"
            >
                <Loader2 v-if="saving" class="size-4 animate-spin" />
                <span v-else>{{ t('Save & Verify') }}</span>
            </button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { Plus, Pencil, Trash2, Loader2, Box, CheckCircle2, ShieldCheck, Globe, Key, Gift, Sparkles, ExternalLink, Radar, ChevronDown } from 'lucide-vue-next';
import ProviderIcon from '../icons/ProviderIcon.vue';
import { 
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter 
} from '@/components/ui/dialog';
import { 
  listModels, createModel, updateModel, deleteModel, detectContextWindow,
  type ModelConfig 
} from '@/api/models';
import { showSuccessToast, showErrorToast } from '@/utils/toast';

const { t } = useI18n();

const PROVIDER_CONFIG: Record<string, { base_url: string; models: string[] }> = {
  openai: {
    base_url: 'https://api.openai.com/v1',
    models: [
      'gpt-5.4', 'gpt-5.3', 'gpt-5.2', 'gpt-5.1', 'gpt-4.5',
    ],
  },
  anthropic: {
    base_url: 'https://api.anthropic.com/v1',
    models: [
      'Claude Opus 4.6', 'Claude Sonnet 4.6',
      'Claude Opus 4.5', 'Claude Sonnet 4',
      'Claude 3.7 Sonnet',
    ],
  },
  deepseek: {
    base_url: 'https://api.deepseek.com',
    models: ['deepseek-chat', 'deepseek-reasoner'],
  },
  gemini: {
    base_url: '',
    models: [
      'gemini-3.1-pro-preview', 'gemini-3.1-flash-preview', 'gemini-3.1-flash-lite-preview', 'gemini-3-deep-think-preview',
    ],
  },
  glm: {
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    models: [
      'glm-5.1', 'glm-5', 'glm-5-turbo',
      'glm-4.7', 'glm-4.7-flashx', 'glm-4.7-flash'
    ],
  },
  qwen: {
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: [
      'qwen3-max', 'qwen3.6-plus', 'qwen3.5-plus', 'qwen3.5-flash',
      'qwen-plus', 'qwen-turbo',
      'qwen3-coder-plus',
    ],
  },
  kimi: {
    base_url: 'https://api.moonshot.cn/v1',
    models: [
      'kimi-k2.5', 'kimi-k2-0905-preview', 'kimi-k2-turbo-preview',
      'kimi-k2-0711-preview', 'kimi-k2-thinking', 'kimi-k2-thinking-turbo'
    ],
  },
  minimax: {
    base_url: 'https://api.minimaxi.com/v1',
    models: [
      'MiniMax-M2.7', 'MiniMax-M2.7-highspeed',
      'MiniMax-M2.5', 'MiniMax-M2.5-highspeed',
      'MiniMax-M2.1', 'MiniMax-M2.1-highspeed',
      'MiniMax-M2',
    ],
  },
  taichu: {
    base_url: '',
    models: ['taichu_llm'],
  },
};

const models = ref<ModelConfig[]>([]);
const loading = ref(false);
const saving = ref(false);
const detecting = ref(false);
const isEditOpen = ref(false);
const editingModel = ref<ModelConfig | null>(null);
const modelDropdownOpen = ref(false);
const customModelInput = ref('');
const dropdownRef = ref<HTMLElement | null>(null);

const form = reactive({
  name: '',
  provider: 'openai',
  model_name: '',
  base_url: '',
  api_key: '',
  context_window: null as number | null,
});

const systemModels = computed(() => models.value.filter(m => m.is_system));
const userModels = computed(() => models.value.filter(m => !m.is_system));

const providerModels = computed(() => {
  const config = PROVIDER_CONFIG[form.provider];
  return config?.models || [];
});

const selectProvider = (p: string) => {
  form.provider = p;
  modelDropdownOpen.value = false;
  customModelInput.value = '';
  if (p !== 'other') {
    const config = PROVIDER_CONFIG[p];
    if (config) {
      form.base_url = config.base_url;
      const first = config.models[0] || '';
      form.model_name = first;
      form.name = first;
    }
  }
};

const onModelSelect = () => {
  if (form.model_name && (!form.name || providerModels.value.includes(form.name))) {
    form.name = form.model_name;
  }
};

const selectModel = (m: string) => {
  form.model_name = m;
  form.name = m;
  modelDropdownOpen.value = false;
  customModelInput.value = '';
};

const applyCustomModel = () => {
  const val = customModelInput.value.trim();
  if (!val) return;
  form.model_name = val;
  form.name = val;
  modelDropdownOpen.value = false;
  customModelInput.value = '';
};

const onClickOutside = (e: MouseEvent) => {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    modelDropdownOpen.value = false;
  }
};

const fetchModels = async () => {
  loading.value = true;
  try {
    models.value = await listModels();
  } catch (err) {
    console.error(err);
    showErrorToast(t('Failed to load models'));
  } finally {
    loading.value = false;
  }
};

const openEditModal = (model: ModelConfig | null) => {
  editingModel.value = model;
  if (model) {
    form.name = model.name;
    form.provider = model.provider;
    form.model_name = model.model_name;
    form.base_url = model.base_url || '';
    form.api_key = '';
    form.context_window = model.context_window ?? null;
  } else {
    const defaultProvider = 'openai';
    const firstModel = PROVIDER_CONFIG[defaultProvider]?.models[0] || '';
    form.name = firstModel;
    form.provider = defaultProvider;
    form.model_name = firstModel;
    form.base_url = PROVIDER_CONFIG[defaultProvider]?.base_url || '';
    form.api_key = '';
    form.context_window = null;
  }
  isEditOpen.value = true;
};

const saveModel = async () => {
  if (!form.name || !form.model_name || !form.provider) {
    showErrorToast(t('Please fill in all required fields'));
    return;
  }

  // If creating, api_key is required
  if (!editingModel.value && !form.api_key) {
      showErrorToast(t('API Key is required'));
      return;
  }

  saving.value = true;
  try {
    const ctxWindow = form.context_window && form.context_window >= 1024 ? form.context_window : undefined;
    if (editingModel.value) {
      await updateModel(editingModel.value.id, {
        name: form.name,
        base_url: form.base_url || undefined,
        api_key: form.api_key || undefined,
        model_name: form.model_name,
        context_window: ctxWindow ?? null,
      });
      showSuccessToast(t('Model verified & updated'));
    } else {
      await createModel({
        name: form.name,
        provider: form.provider,
        base_url: form.base_url || undefined,
        api_key: form.api_key || undefined,
        model_name: form.model_name,
        context_window: ctxWindow ?? null,
      });
      showSuccessToast(t('Model verified & created'));
    }
    isEditOpen.value = false;
    await fetchModels();
  } catch (err: any) {
    console.error(err);
    const detail = err.response?.data?.detail || err.response?.data?.message || err.message || String(err);
    showErrorToast(t('Operation failed') + ': ' + detail);
  } finally {
    saving.value = false;
  }
};

const detectCtxWindow = async () => {
  if (!form.model_name) {
    showErrorToast(t('Please enter Model ID first'));
    return;
  }
  detecting.value = true;
  try {
    const ctxWindow = await detectContextWindow({
      provider: form.provider,
      base_url: form.base_url || undefined,
      api_key: form.api_key || undefined,
      model_name: form.model_name,
      model_id: editingModel.value?.id,
    });
    form.context_window = ctxWindow;
    showSuccessToast(t('Detected context window') + `: ${ctxWindow.toLocaleString()}`);
  } catch (err: any) {
    const detail = err.response?.data?.detail;
    showErrorToast(detail || t('Failed to detect context window'));
  } finally {
    detecting.value = false;
  }
};

const confirmDelete = async (model: ModelConfig) => {
  if (!confirm(t('Are you sure you want to delete this model?'))) return;
  
  try {
    await deleteModel(model.id);
    showSuccessToast(t('Model deleted'));
    await fetchModels();
  } catch (err) {
    console.error(err);
    showErrorToast(t('Delete failed'));
  }
};

onMounted(() => {
  fetchModels();
  document.addEventListener('click', onClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside);
});
</script>
