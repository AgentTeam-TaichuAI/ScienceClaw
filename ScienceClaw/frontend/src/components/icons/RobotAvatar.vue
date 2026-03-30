<template>
  <div 
    class="relative inline-flex items-center justify-center h-full w-full select-none"
    :class="{ 'cursor-pointer': interactive }"
    @click="handleClick"
  >
    <!-- Speech Bubble -->
    <transition name="fade">
      <div 
        v-if="showGreeting && interactive" 
        class="absolute -top-10 left-1/2 transform -translate-x-1/2 bg-[var(--text-primary)] text-[var(--background-white-main)] text-xs px-3 py-1.5 rounded-lg whitespace-nowrap z-50 shadow-lg after:content-[''] after:absolute after:top-full after:left-1/2 after:-translate-x-1/2 after:border-4 after:border-transparent after:border-t-[var(--text-primary)]"
      >
        {{ greetingText }}
      </div>
    </transition>

    <!-- Robot Image with animations -->
    <img 
      src="/robot.png" 
      alt="ScienceClaw" 
      class="object-contain w-full h-full transition-transform duration-200"
      :class="{
        'animate-float': interactive && !isClicking,
        'scale-90': interactive && isClicking
      }" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps({
  interactive: {
    type: Boolean,
    default: true
  }
});

const showGreeting = ref(false);
const isClicking = ref(false);
const greetingText = ref('Hello! 👋');
let timeoutId: ReturnType<typeof setTimeout>;

const greetings = ['Hello! 👋', 'Hi there!', 'I am ScienceClaw', 'Ready to research! 🧬'];

const handleClick = () => {
  if (!props.interactive) return;

  // Prevent event bubbling if necessary, though usually fine
  // e.stopPropagation();

  // Click animation
  isClicking.value = true;
  setTimeout(() => {
    isClicking.value = false;
  }, 150);

  // Show greeting
  const randomGreeting = greetings[Math.floor(Math.random() * greetings.length)];
  greetingText.value = randomGreeting;
  
  showGreeting.value = true;
  
  if (timeoutId) clearTimeout(timeoutId);
  timeoutId = setTimeout(() => {
    showGreeting.value = false;
  }, 2000);
};
</script>

<style scoped>
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6%); }
}

.animate-float {
  animation: float 3s ease-in-out infinite;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 5px);
}
</style>
