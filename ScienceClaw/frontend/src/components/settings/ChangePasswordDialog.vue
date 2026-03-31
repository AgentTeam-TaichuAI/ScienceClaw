<template>
  <Dialog v-model:open="open">
    <DialogContent class="bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl w-[480px] rounded-2xl border border-gray-200/60 dark:border-gray-700/40 shadow-2xl p-0 overflow-hidden">
      <DialogHeader class="px-6 pt-6 pb-4 border-b border-gray-100 dark:border-gray-800">
        <DialogTitle class="text-lg font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
          <div class="size-8 rounded-lg bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center">
            <KeyRound :size="16" class="text-amber-500" />
          </div>
          {{ t('Update Password') }}
        </DialogTitle>
      </DialogHeader>

      <div class="px-6 py-5">
        <form class="flex flex-col gap-5">
          <!-- Current Password -->
          <label class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-gray-600 dark:text-gray-300">{{ t('Current Password') }}</span>
            <div class="relative w-full">
              <input v-model="currentPassword"
                class="w-full h-11 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 pr-12 text-sm text-gray-800 dark:text-gray-100 placeholder:text-gray-300 dark:placeholder:text-gray-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-600"
                :placeholder="t('Enter current password')" :type="showCurrentPassword ? 'text' : 'password'">
              <button type="button" @click="toggleCurrentPasswordVisibility"
                class="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors cursor-pointer">
                <Eye v-if="showCurrentPassword" :size="18" />
                <EyeOff v-else :size="18" />
              </button>
            </div>
          </label>

          <!-- New Password -->
          <label class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-gray-600 dark:text-gray-300">{{ t('New Password') }}</span>
            <div class="relative w-full">
              <input v-model="newPassword"
                class="w-full h-11 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 pr-12 text-sm text-gray-800 dark:text-gray-100 placeholder:text-gray-300 dark:placeholder:text-gray-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-600"
                :placeholder="t('Enter new password')" :type="showNewPassword ? 'text' : 'password'">
              <button type="button" @click="toggleNewPasswordVisibility"
                class="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors cursor-pointer">
                <Eye v-if="showNewPassword" :size="18" />
                <EyeOff v-else :size="18" />
              </button>
            </div>
          </label>

          <!-- Confirm New Password -->
          <label class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-gray-600 dark:text-gray-300">{{ t('Confirm New Password') }}</span>
            <div class="relative w-full">
              <input v-model="confirmPassword"
                class="w-full h-11 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 pr-12 text-sm text-gray-800 dark:text-gray-100 placeholder:text-gray-300 dark:placeholder:text-gray-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-600"
                :class="confirmPassword && newPassword !== confirmPassword ? 'border-red-300 dark:border-red-600 focus:ring-red-500/20' : ''"
                :placeholder="t('Enter new password again')" :type="showConfirmPassword ? 'text' : 'password'">
              <button type="button" @click="toggleConfirmPasswordVisibility"
                class="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors cursor-pointer">
                <Eye v-if="showConfirmPassword" :size="18" />
                <EyeOff v-else :size="18" />
              </button>
            </div>
            <p v-if="confirmPassword && newPassword !== confirmPassword"
              class="text-xs text-red-500 mt-0.5">
              {{ t('Passwords do not match') }}
            </p>
          </label>
        </form>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 flex justify-end gap-3">
        <DialogClose as-child>
          <button type="button"
            class="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 transition-all duration-200 shadow-sm">
            {{ t('Cancel') }}
          </button>
        </DialogClose>
        <button type="button" @click="handleSubmit" :disabled="!isFormValid"
          class="px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.97] transition-all duration-200 flex items-center gap-2"
          :class="!isFormValid ? 'opacity-50 cursor-not-allowed' : ''">
          <div v-if="isLoading" class="size-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <span v-if="!isLoading">{{ t('Confirm') }}</span>
          <span v-else>{{ t('Processing...') }}</span>
        </button>
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Eye, EyeOff, KeyRound } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose
} from '@/components/ui/dialog'
import { changePassword } from '@/api/auth'
import { showSuccessToast, showErrorToast } from '@/utils/toast'

// Use i18n for translations
const { t } = useI18n()

// Dialog state
const open = ref(false)
const isLoading = ref(false)

// Form data
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

// Password visibility state
const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

// Form validation
const isFormValid = computed(() => {
  return !isLoading.value &&
    currentPassword.value.trim() !== '' &&
    newPassword.value.trim() !== '' &&
    newPassword.value.length >= 6 &&
    confirmPassword.value.trim() !== '' &&
    newPassword.value === confirmPassword.value
})

// Toggle password visibility
const toggleCurrentPasswordVisibility = () => {
  showCurrentPassword.value = !showCurrentPassword.value
}

const toggleNewPasswordVisibility = () => {
  showNewPassword.value = !showNewPassword.value
}

const toggleConfirmPasswordVisibility = () => {
  showConfirmPassword.value = !showConfirmPassword.value
}



// Reset form when dialog closes
const resetForm = () => {
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  showCurrentPassword.value = false
  showNewPassword.value = false
  showConfirmPassword.value = false
  isLoading.value = false
}

// Handle form submission
const handleSubmit = async () => {
  if (!isFormValid.value) {
    return
  }

  isLoading.value = true

  try {
    await changePassword({
      old_password: currentPassword.value,
      new_password: newPassword.value
    })

    showSuccessToast(t('Password change successful'))
    resetForm()
    open.value = false
  } catch (error: any) {
    console.error('Change password error:', error)

    // Extract error message from response
    let errorMessage = t('Password change failed')
    if (error?.response?.data?.message) {
      errorMessage = error.response.data.message
    } else if (error?.message) {
      errorMessage = error.message
    }

    showErrorToast(errorMessage)
  } finally {
    isLoading.value = false
  }
}

// Expose methods to parent component
defineExpose({
  open: () => {
    resetForm()
    open.value = true
  },
  close: () => {
    resetForm()
    open.value = false
  }
})
</script>
