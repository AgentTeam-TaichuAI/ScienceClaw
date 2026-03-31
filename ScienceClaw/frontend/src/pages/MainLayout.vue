<template>
  <div class="h-screen flex overflow-hidden bg-white">
    <LeftPanel />
    <div class="flex-1 min-w-0 h-full py-0 pr-0 relative">
      <div class="flex h-full bg-[var(--background-gray-main)]">
        <div class="flex flex-1 min-w-0 min-h-0">
          <router-view :key="routeViewKey" />
          <FilePanel />
        </div>
      </div>
    </div>
  </div>
  <TakeOverView />
  <CustomDialog />
  <SessionFileList />
  <SettingsDialog />
  <ContextMenu />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import LeftPanel from '@/components/LeftPanel.vue';
import CustomDialog from '@/components/ui/CustomDialog.vue';
import ContextMenu from '@/components/ui/ContextMenu.vue';
import TakeOverView from '@/components/TakeOverView.vue';
import SessionFileList from '@/components/SessionFileList.vue';
import FilePanel from '@/components/FilePanel.vue';
import SettingsDialog from '@/components/settings/SettingsDialog.vue';

const route = useRoute();
const routeViewKey = computed(() => {
  const sessionId = route.params.sessionId;
  return Array.isArray(sessionId) ? sessionId.join('/') : sessionId;
});
</script>
