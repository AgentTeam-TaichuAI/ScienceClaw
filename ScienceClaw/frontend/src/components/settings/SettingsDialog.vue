<template>
  <Dialog v-model:open="isSettingsDialogOpen">
    <DialogContent class="w-[380px] md:w-[95vw] md:max-w-[920px] rounded-2xl border border-gray-200/60 dark:border-gray-700/40 shadow-2xl overflow-hidden p-0">
      <DialogTitle></DialogTitle>
      <DialogDescription></DialogDescription>
      
      <SettingsTabs 
        :tabs="tabs" 
        :default-tab="defaultTab"
        :current-sub-page="currentSubPage"
        :sub-page-configs="subPageConfigs"
        @tab-change="onTabChange"
        @navigate-to-profile="navigateToProfile"
        @back="goBack">
        
        <template #account>
          <AccountSettings @navigate-to-profile="navigateToProfile" />
        </template>
        
        <template #account-profile>
          <ProfileSettings @back="goBack" />
        </template>

        <template #im-binding>
          <LarkBindingSettings @back="goBack" />
        </template>
        
        <template #personalization>
          <PersonalizationSettings />
        </template>
        
        <template #settings>
          <GeneralSettings />
        </template>
        
        <template #models>
          <ModelSettings />
        </template>

        <template #tasks>
          <TaskSettings />
        </template>

        <template #statistics>
          <TokenStatistics />
        </template>

        <template #notifications>
          <NotificationSettings />
        </template>

        <template #im>
          <IMSystemSettings :is-admin="isAdmin" @navigate-to-binding="navigateToBinding" />
        </template>
        
      </SettingsTabs>
      
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { UserRound, Settings2, Box, ListTodo, Brain, Bell, BarChart3, Bot } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { useSettingsDialog } from '@/composables/useSettingsDialog'
import SettingsTabs from './SettingsTabs.vue'
import AccountSettings from './AccountSettings.vue'
import GeneralSettings from './GeneralSettings.vue'
import ProfileSettings from './ProfileSettings.vue'
import ModelSettings from './ModelSettings.vue'
import TaskSettings from './TaskSettings.vue'
import PersonalizationSettings from './PersonalizationSettings.vue'
import NotificationSettings from './NotificationSettings.vue'
import TokenStatistics from './TokenStatistics.vue'
import LarkBindingSettings from './LarkBindingSettings.vue'
import IMSystemSettings from './IMSystemSettings.vue'
import type { TabItem, SubPageConfig } from './SettingsTabs.vue'
import { useAuth } from '@/composables/useAuth'

// Use global settings dialog state
const { isSettingsDialogOpen, defaultTab } = useSettingsDialog()
const { isAdmin } = useAuth()

// Navigation state for sub-pages
const currentSubPage = ref<string | null>(null)

// Tab configuration
const tabs = computed<TabItem[]>(() => {
  const baseTabs: TabItem[] = [
    {
      id: 'account',
      label: 'Account',
      icon: UserRound
    },
    {
      id: 'personalization',
      label: 'Personalization',
      icon: Brain
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings2
    },
    {
      id: 'models',
      label: 'Models',
      icon: Box
    },
    {
      id: 'tasks',
      label: 'Tasks',
      icon: ListTodo
    },
    {
      id: 'statistics',
      label: 'Statistics',
      icon: BarChart3
    },
    {
      id: 'notifications',
      label: 'Notifications',
      icon: Bell
    },
    {
      id: 'im',
      label: 'IM',
      icon: Bot
    }
  ]
  return baseTabs
})

// Sub-page configuration
const subPageConfigs: SubPageConfig[] = [
  {
    id: 'profile',
    title: 'Profile',
    parentTabId: 'account'
  },
  {
    id: 'binding',
    title: 'IM Binding',
    parentTabId: 'im'
  }
]

// Handle tab change
const onTabChange = (tabId: string) => {
  console.log('Tab changed to:', tabId)
  // Reset sub-page when changing tabs
  currentSubPage.value = null
}

// Navigate to profile sub-page
const navigateToProfile = () => {
  currentSubPage.value = 'profile'
}

const navigateToBinding = () => {
  currentSubPage.value = 'binding'
}

// Go back to main view
const goBack = () => {
  currentSubPage.value = null
}
</script>
