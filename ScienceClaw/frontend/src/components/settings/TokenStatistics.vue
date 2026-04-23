<template>
  <div class="flex flex-col gap-6 w-full">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-1 flex items-center gap-2">
        {{ t('Token Statistics') }}
        <span class="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent"></span>
      </h3>

      <!-- Controls -->
      <div class="flex items-center gap-2">
        <!-- Currency Selector -->
        <div class="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button @click="selectedCurrency = 'CNY'"
            class="px-2 py-1 text-xs font-medium transition-colors"
            :class="selectedCurrency === 'CNY' ? 'bg-blue-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'">
            CNY
          </button>
          <button @click="selectedCurrency = 'USD'"
            class="px-2 py-1 text-xs font-medium transition-colors"
            :class="selectedCurrency === 'USD' ? 'bg-blue-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'">
            USD
          </button>
        </div>
        <!-- Estimated Badge -->
        <span class="text-xs text-gray-400 dark:text-gray-500">{{ t('Estimated') }}</span>
        <!-- Time Range Selector -->
        <select v-model="selectedTimeRange" class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20">
          <option value="today">{{ t('Today') }}</option>
          <option value="7days">{{ t('Last 7 Days') }}</option>
          <option value="30days">{{ t('Last 30 Days') }}</option>
          <option value="all">{{ t('All Time') }}</option>
        </select>
        <button @click="refreshData" class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" :disabled="isLoading">
          <RefreshCw class="size-4 text-gray-400" :class="{ 'animate-spin': isLoading }" />
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800/50 rounded-xl">
      <button
        v-for="tab in subTabs"
        :key="tab.id"
        @click="activeSubTab = tab.id"
        class="flex-1 px-4 py-2 text-xs font-medium rounded-lg transition-all duration-200"
        :class="activeSubTab === tab.id
          ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'"
      >
        {{ t(tab.label) }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex items-center justify-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- Overview Tab -->
      <template v-if="activeSubTab === 'overview'">
        <!-- Core Stats Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div v-for="card in statsCards" :key="card.id"
            class="p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div class="flex items-center gap-2 mb-2">
              <div class="size-8 rounded-lg flex items-center justify-center" :class="card.iconBg">
                <component :is="card.icon" class="size-4" :class="card.iconColor" />
              </div>
            </div>
            <div class="text-lg font-bold text-gray-800 dark:text-gray-100 tabular-nums">
              {{ card.value }}
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400">{{ t(card.label) }}</div>
            <div v-if="card.trend !== undefined" class="flex items-center gap-1 mt-1">
              <component :is="card.trend >= 0 ? TrendingUp : TrendingDown" class="size-3" :class="card.trend >= 0 ? 'text-green-500' : 'text-red-500'" />
              <span class="text-xs" :class="card.trend >= 0 ? 'text-green-500' : 'text-red-500'">
                {{ Math.abs(card.trend) }}% {{ t('vs last period') }}
              </span>
            </div>
          </div>
        </div>

        <!-- Token Distribution -->
        <div v-if="tokenDistribution.length > 0" class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <h4 class="text-sm font-bold text-gray-700 dark:text-gray-200 mb-4">{{ t('Token Distribution') }}</h4>

          <div class="space-y-4">
            <div v-for="(item, index) in tokenDistribution" :key="item.label" class="space-y-1.5">
              <div class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-300">{{ t(item.label) }}</span>
                <span class="font-medium text-gray-800 dark:text-gray-100 tabular-nums">{{ formatNumber(item.value) }}</span>
              </div>
              <div class="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500" :class="getDistributionBarColor(index)" :style="{ width: `${item.percentage}%` }"></div>
              </div>
              <div class="text-xs text-gray-400 text-right">{{ item.percentage.toFixed(1) }}%</div>
            </div>
          </div>
        </div>
      </template>

      <!-- Models Tab -->
      <template v-else-if="activeSubTab === 'models'">
        <div v-if="topModels.length > 0" class="space-y-3">
          <!-- Model Stats Header -->
          <div class="grid grid-cols-5 gap-2 px-4 py-2 text-xs font-medium text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-800/30 rounded-lg">
            <div class="col-span-2">{{ t('Model') }}</div>
            <div class="text-right">{{ t('Sessions') }}</div>
            <div class="text-right">{{ t('Tokens') }}</div>
            <div class="text-right">{{ t('Cost') }}</div>
          </div>

          <!-- Model List -->
          <div class="space-y-2">
            <div v-for="(model, index) in topModels" :key="model.name"
              class="grid grid-cols-5 gap-2 p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl items-center hover:shadow-sm transition-shadow">
              <!-- Model Name & Rank -->
              <div class="col-span-2 flex items-center gap-3">
                <div class="size-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                  :class="getRankBadgeClass(index)">
                  {{ index + 1 }}
                </div>
                <div class="min-w-0">
                  <div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">{{ model.name }}</div>
                  <div class="text-xs text-gray-400">{{ t('Input') }}: {{ formatNumber(model.inputTokens) }} / {{ t('Output') }}: {{ formatNumber(model.outputTokens) }}</div>
                </div>
              </div>

              <!-- Sessions -->
              <div class="text-right">
                <div class="text-sm font-medium text-gray-700 dark:text-gray-200 tabular-nums">{{ model.sessionCount }}</div>
              </div>

              <!-- Tokens -->
              <div class="text-right">
                <div class="text-sm font-medium text-gray-700 dark:text-gray-200 tabular-nums">{{ formatTokenCount(model.tokens) }}</div>
              </div>

              <!-- Cost -->
              <div class="text-right">
                <div class="text-sm font-semibold text-gray-800 dark:text-gray-100 tabular-nums">{{ formatCost(model.costUsd, model.costCny) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="flex flex-col items-center justify-center py-12 text-gray-400">
          <Box class="size-12 mb-3 opacity-50" />
          <p class="text-sm">{{ t('No model statistics available') }}</p>
        </div>
      </template>

      <!-- Sessions Tab -->
      <template v-else-if="activeSubTab === 'sessions'">
        <div v-if="sessionsData.length > 0" class="space-y-3">
          <!-- Session Stats Header -->
          <div class="grid grid-cols-12 gap-2 px-4 py-2 text-xs font-medium text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-800/30 rounded-lg">
            <div class="col-span-5">{{ t('Session') }}</div>
            <div class="col-span-2">{{ t('Model') }}</div>
            <div class="col-span-2 text-right">{{ t('Tokens') }}</div>
            <div class="col-span-1 text-right">{{ t('Cost') }}</div>
            <div class="col-span-2 text-right">{{ t('Date') }}</div>
          </div>

          <!-- Session List -->
          <div class="space-y-2 max-h-[400px] overflow-y-auto pr-1">
            <div v-for="session in sessionsData" :key="session.session_id"
              class="grid grid-cols-12 gap-2 p-3 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl items-center hover:shadow-sm transition-shadow">
              <!-- Session Title -->
              <div class="col-span-5 min-w-0">
                <div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">{{ session.title || t('Untitled Session') }}</div>
                <div class="text-xs text-gray-400 flex items-center gap-2 mt-0.5">
                  <span class="inline-flex items-center gap-1">
                    <span class="size-1.5 rounded-full" :class="getSessionStatusColor(session.status)"></span>
                    {{ t(session.status) }}
                  </span>
                  <span>{{ formatNumber(session.input_tokens) }} / {{ formatNumber(session.output_tokens) }}</span>
                </div>
              </div>

              <!-- Model -->
              <div class="col-span-2">
                <div class="text-xs text-gray-600 dark:text-gray-300 truncate">{{ session.model || '-' }}</div>
              </div>

              <!-- Tokens -->
              <div class="col-span-2 text-right">
                <div class="text-sm font-medium text-gray-700 dark:text-gray-200 tabular-nums">{{ formatNumber(session.total_tokens) }}</div>
              </div>

              <!-- Cost -->
              <div class="col-span-1 text-right">
                <div class="text-sm font-medium text-gray-800 dark:text-gray-100 tabular-nums">{{ formatCost(session.cost_usd, session.cost_cny) }}</div>
              </div>

              <!-- Date -->
              <div class="col-span-2 text-right">
                <div class="text-xs text-gray-400">{{ session.created_at }}</div>
              </div>
            </div>
          </div>

          <!-- Pagination -->
          <div v-if="sessionsTotal > sessionsPageSize" class="flex items-center justify-between pt-2">
            <div class="text-xs text-gray-400">
              {{ t('Showing') }} {{ (sessionsPage - 1) * sessionsPageSize + 1 }}-{{ Math.min(sessionsPage * sessionsPageSize, sessionsTotal) }} {{ t('of') }} {{ sessionsTotal }}
            </div>
            <div class="flex gap-1">
              <button @click="sessionsPage = Math.max(1, sessionsPage - 1)" :disabled="sessionsPage <= 1"
                class="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed">
                {{ t('Previous') }}
              </button>
              <button @click="sessionsPage = sessionsPage + 1" :disabled="sessionsPage * sessionsPageSize >= sessionsTotal"
                class="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed">
                {{ t('Next') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="flex flex-col items-center justify-center py-12 text-gray-400">
          <MessageSquare class="size-12 mb-3 opacity-50" />
          <p class="text-sm">{{ t('No session statistics available') }}</p>
        </div>
      </template>

      <!-- Trends Tab -->
      <template v-else-if="activeSubTab === 'trends'">
        <div v-if="trendsData.length > 0" class="space-y-4">
          <!-- Chart Container -->
          <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
            <h4 class="text-sm font-bold text-gray-700 dark:text-gray-200 mb-4">{{ t('Usage Trends') }}</h4>

            <!-- Simple Bar Chart -->
            <div class="relative h-48">
              <!-- Y-axis labels -->
              <div class="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-xs text-gray-400">
                <span>{{ maxTrendTokens > 0 ? formatNumber(maxTrendTokens) : '0' }}</span>
                <span>{{ maxTrendTokens > 0 ? formatNumber(Math.floor(maxTrendTokens / 2)) : '0' }}</span>
                <span>0</span>
              </div>

              <!-- Chart Area -->
              <div class="ml-14 h-40 flex items-end gap-1">
                <div v-for="point in trendsData" :key="point.date"
                  class="flex-1 flex flex-col items-center group">
                  <!-- Bar -->
                  <div class="w-full relative flex justify-center">
                    <div
                      class="w-4/5 max-w-8 bg-gradient-to-t from-blue-500 to-blue-400 rounded-t-sm transition-all duration-300 hover:from-blue-600 hover:to-blue-500 cursor-pointer"
                      :style="{ height: `${getBarHeight(point.tokens)}px` }">
                      <!-- Tooltip -->
                      <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                        {{ point.date }}: {{ formatNumber(point.tokens) }} tokens
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- X-axis labels -->
              <div class="ml-14 h-8 flex gap-1 mt-1">
                <div v-for="point in trendsData" :key="point.date" class="flex-1 text-center">
                  <span class="text-xs text-gray-400 truncate block">{{ formatDateLabel(point.date) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Stats Summary -->
          <div class="grid grid-cols-3 gap-3">
            <div class="p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl text-center">
              <div class="text-lg font-bold text-blue-500 tabular-nums">{{ formatNumber(totalsTokens) }}</div>
              <div class="text-xs text-gray-500">{{ t('Total Tokens') }}</div>
            </div>
            <div class="p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl text-center">
              <div class="text-lg font-bold text-green-500 tabular-nums">{{ formatNumber(Math.round(averageTokensPerDay)) }}</div>
              <div class="text-xs text-gray-500">{{ t('Avg / Day') }}</div>
            </div>
            <div class="p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl text-center">
              <div class="text-lg font-bold text-purple-500 tabular-nums">{{ formatNumber(maxDailyTokens) }}</div>
              <div class="text-xs text-gray-500">{{ t('Peak Day') }}</div>
            </div>
          </div>

          <!-- Daily Details -->
          <div class="p-4 bg-gray-50 dark:bg-gray-800/30 rounded-xl">
            <div class="text-xs font-medium text-gray-500 mb-2">{{ t('Daily Breakdown') }}</div>
            <div class="space-y-1 max-h-32 overflow-y-auto">
              <div v-for="point in trendsData" :key="point.date"
                class="flex items-center justify-between text-sm py-1 border-b border-gray-100 dark:border-gray-700/50 last:border-0">
                <span class="text-gray-600 dark:text-gray-300">{{ point.date }}</span>
                <div class="flex items-center gap-4">
                  <span class="text-gray-400 text-xs">{{ point.sessions }} {{ t('sessions') }}</span>
                  <span class="font-medium text-gray-800 dark:text-gray-100 tabular-nums">{{ formatNumber(point.tokens) }}</span>
                  <span class="text-xs text-gray-400 tabular-nums">{{ formatCost(point.cost_usd, point.cost_cny) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="flex flex-col items-center justify-center py-12 text-gray-400">
          <Activity class="size-12 mb-3 opacity-50" />
          <p class="text-sm">{{ t('No trend data available') }}</p>
        </div>
      </template>

      <!-- Empty State (for overview) -->
      <div v-if="activeSubTab === 'overview' && tokenDistribution.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
        <BarChart3 class="size-12 mb-3 opacity-50" />
        <p class="text-sm">{{ t('No statistics data available') }}</p>
      </div>
    </template>

    <!-- Last Update Time -->
    <div class="flex items-center justify-center gap-2 text-xs text-gray-400 dark:text-gray-500">
      <Clock class="size-3" />
      <span>{{ t('Last updated') }}: {{ lastUpdateTime }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Coins,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Clock,
  MessageSquare,
  DollarSign,
  BarChart3,
  Zap,
  Box,
  Activity
} from 'lucide-vue-next'
import { apiClient } from '@/api/client'

const { t } = useI18n()

// Types
interface TokenDistribution {
  label: string
  value: number
  percentage: number
}

interface ModelUsage {
  name: string
  session_count: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost_usd: number
  cost_cny: number
}

interface SessionUsage {
  session_id: string
  title: string
  model: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost_usd: number
  cost_cny: number
  created_at: string
  status: string
}

interface TrendPoint {
  date: string
  sessions: number
  tokens: number
  cost_usd: number
  cost_cny: number
}

interface SummaryData {
  total_cost_usd: number
  total_cost_cny: number
  total_sessions: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  avg_per_session: number
  cost_trend: number
  session_trend: number
  token_trend: number
  distribution: TokenDistribution[]
}

// State
const isLoading = ref(false)
const selectedTimeRange = ref('7days')
const selectedCurrency = ref<'USD' | 'CNY'>('CNY')
const activeSubTab = ref('overview')
const lastUpdateTime = ref(new Date().toLocaleString())

const summaryData = ref<SummaryData | null>(null)
const modelsData = ref<ModelUsage[]>([])
const sessionsData = ref<SessionUsage[]>([])
const trendsData = ref<TrendPoint[]>([])
const sessionsTotal = ref(0)
const sessionsPage = ref(1)
const sessionsPageSize = 10

// Sub tabs
const subTabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'models', label: 'Models' },
  { id: 'sessions', label: 'Sessions' },
  { id: 'trends', label: 'Trends' }
]

// Computed
const statsCards = computed(() => {
  if (!summaryData.value) return []

  const costValue = selectedCurrency.value === 'CNY'
    ? `¥${summaryData.value.total_cost_cny.toFixed(2)}`
    : `$${summaryData.value.total_cost_usd.toFixed(2)}`

  return [
    {
      id: 'cost',
      label: 'Total Cost',
      value: costValue,
      icon: DollarSign,
      iconBg: 'bg-green-50 dark:bg-green-900/30',
      iconColor: 'text-green-500',
      trend: summaryData.value.cost_trend
    },
    {
      id: 'sessions',
      label: 'Total Sessions',
      value: formatNumber(summaryData.value.total_sessions),
      icon: MessageSquare,
      iconBg: 'bg-orange-50 dark:bg-orange-900/30',
      iconColor: 'text-orange-500',
      trend: summaryData.value.session_trend
    },
    {
      id: 'tokens',
      label: 'Total Tokens',
      value: formatTokenCount(summaryData.value.total_tokens),
      icon: Coins,
      iconBg: 'bg-violet-50 dark:bg-violet-900/30',
      iconColor: 'text-violet-500',
      trend: summaryData.value.token_trend
    },
    {
      id: 'avg',
      label: 'Avg / Session',
      value: formatTokenCount(summaryData.value.avg_per_session),
      icon: Zap,
      iconBg: 'bg-blue-50 dark:bg-blue-900/30',
      iconColor: 'text-blue-500',
      trend: 0
    }
  ]
})

const tokenDistribution = computed(() => {
  return summaryData.value?.distribution || []
})

const topModels = computed(() => {
  return modelsData.value.map(model => ({
    name: model.name,
    sessionCount: model.session_count,
    costUsd: model.cost_usd,
    costCny: model.cost_cny,
    tokens: model.total_tokens,
    inputTokens: model.input_tokens,
    outputTokens: model.output_tokens
  }))
})

const maxTrendTokens = computed(() => {
  if (trendsData.value.length === 0) return 0
  return Math.max(...trendsData.value.map(p => p.tokens))
})

const maxDailyTokens = computed(() => {
  if (trendsData.value.length === 0) return 0
  return Math.max(...trendsData.value.map(p => p.tokens))
})

const totalsTokens = computed(() => {
  return trendsData.value.reduce((sum, p) => sum + p.tokens, 0)
})

const averageTokensPerDay = computed(() => {
  if (trendsData.value.length === 0) return 0
  return totalsTokens.value / trendsData.value.length
})

// Methods
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const formatTokenCount = (count: number): string => {
  return formatNumber(count) + ' tokens'
}

const formatCost = (costUsd: number, costCny: number): string => {
  if (selectedCurrency.value === 'CNY') {
    return `¥${costCny.toFixed(2)}`
  }
  return `$${costUsd.toFixed(2)}`
}

const formatDateLabel = (dateStr: string): string => {
  const date = new Date(dateStr)
  const month = date.getMonth() + 1
  const day = date.getDate()
  return `${month}/${day}`
}

const getRankBadgeClass = (index: number): string => {
  if (index === 0) return 'bg-blue-500 text-white'
  if (index === 1) return 'bg-gray-400 text-white'
  if (index === 2) return 'bg-amber-600 text-white'
  return 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
}

const getDistributionBarColor = (index: number): string => {
  const colors = ['bg-blue-500', 'bg-emerald-500', 'bg-violet-500']
  return colors[index] || 'bg-gray-400'
}

const getSessionStatusColor = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'bg-green-500'
    case 'running':
      return 'bg-blue-500'
    case 'failed':
      return 'bg-red-500'
    default:
      return 'bg-gray-400'
  }
}

const getBarHeight = (tokens: number): number => {
  const maxTokens = maxTrendTokens.value
  if (maxTokens === 0) return 0
  const maxHeight = 140 // Max bar height in pixels
  return Math.max(4, (tokens / maxTokens) * maxHeight)
}

const fetchData = async () => {
  isLoading.value = true

  try {
    // Always fetch summary data for overview
    const summaryRes = await apiClient.get(`/statistics/summary?time_range=${selectedTimeRange.value}`)
    if (summaryRes.data) {
      summaryData.value = summaryRes.data
    }

    // Fetch data based on active tab
    if (activeSubTab.value === 'models' || activeSubTab.value === 'overview') {
      const modelsRes = await apiClient.get(`/statistics/models?time_range=${selectedTimeRange.value}`)
      if (modelsRes.data) {
        modelsData.value = modelsRes.data.models || []
      }
    }

    if (activeSubTab.value === 'sessions') {
      const sessionsRes = await apiClient.get(`/statistics/sessions?time_range=${selectedTimeRange.value}&page=${sessionsPage.value}&page_size=${sessionsPageSize}`)
      if (sessionsRes.data) {
        sessionsData.value = sessionsRes.data.sessions || []
        sessionsTotal.value = sessionsRes.data.total || 0
      }
    }

    if (activeSubTab.value === 'trends') {
      const trendsRes = await apiClient.get(`/statistics/trends?time_range=${selectedTimeRange.value}`)
      if (trendsRes.data) {
        trendsData.value = trendsRes.data.daily || []
      }
    }

    lastUpdateTime.value = new Date().toLocaleString()
  } catch (error) {
    console.error('Failed to fetch statistics:', error)
  } finally {
    isLoading.value = false
  }
}

const refreshData = async () => {
  await fetchData()
}

// Watch for time range changes
watch(selectedTimeRange, () => {
  sessionsPage.value = 1
  fetchData()
})

// Watch for tab changes
watch(activeSubTab, () => {
  fetchData()
})

// Watch for page changes
watch(sessionsPage, () => {
  fetchData()
})

onMounted(() => {
  fetchData()
})
</script>
