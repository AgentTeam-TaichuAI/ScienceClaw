<template>
  <div ref="terminalContainer" class="sandbox-terminal w-full h-full"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

export interface SandboxExecEntry {
  toolName: string;
  command: string;
  output?: string;
  status: string;
}

const props = defineProps<{
  active: boolean;
  history?: SandboxExecEntry[];
}>();

const terminalContainer = ref<HTMLDivElement | null>(null);

let terminal: Terminal | null = null;
let fitAddon: FitAddon | null = null;
let resizeObserver: ResizeObserver | null = null;

const C = {
  green: '\x1b[32m',
  boldGreen: '\x1b[1;32m',
  blue: '\x1b[34m',
  boldBlue: '\x1b[1;34m',
  cyan: '\x1b[36m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  dim: '\x1b[2m',
  reset: '\x1b[0m',
  bold: '\x1b[1m',
};

const initTerminal = () => {
  if (!terminalContainer.value || terminal) return;

  terminal = new Terminal({
    cursorBlink: false,
    disableStdin: true,
    fontSize: 13,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
      cursor: '#1e1e1e',
      selectionBackground: '#264f78',
    },
    scrollback: 10000,
    convertEol: true,
  });

  fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);
  terminal.open(terminalContainer.value);

  requestAnimationFrame(() => {
    fitAddon?.fit();
  });

  resizeObserver = new ResizeObserver(() => {
    requestAnimationFrame(() => {
      fitAddon?.fit();
    });
  });
  resizeObserver.observe(terminalContainer.value);
};

const writeExecution = (command: string, output?: string, status?: string) => {
  if (!terminal) {
    initTerminal();
  }
  if (!terminal) return;

  if (status === 'calling') {
    // Cursor style: $ command
    terminal.writeln(`${C.boldGreen}$${C.reset} ${C.bold}${command}${C.reset}`);
  } else if (status === 'called') {
    const exitMatch = output?.match(/\[Command (succeeded|failed) with exit code (-?\d+)\]/);
    const exitCode = exitMatch ? parseInt(exitMatch[2], 10) : null;
    const isFailed = exitCode !== null && exitCode !== 0;

    const exitStatusPattern = /^\[Command (?:succeeded|failed) with exit code -?\d+\]$/;
    const lines = output ? output.split('\n').filter(l => !exitStatusPattern.test(l.trim())) : [];
    const hasRealOutput = lines.some(l => l.trim() !== '');

    if (hasRealOutput) {
      const maxLines = 50;
      const display = lines.length > maxLines
        ? [...lines.slice(0, maxLines), `${C.dim}... (${lines.length - maxLines} more lines)${C.reset}`]
        : lines;
      for (const line of display) {
        terminal.writeln(line);
      }
    }

    if (isFailed && !hasRealOutput) {
      terminal.writeln(`${C.red}✗ Process exited with code ${exitCode}${C.reset}`);
    }

    terminal.writeln('');
  }

  requestAnimationFrame(() => {
    terminal?.scrollToBottom();
  });
};

let renderedCount = 0;

const renderNewEntries = () => {
  const entries = props.history || [];
  while (renderedCount < entries.length) {
    const entry = entries[renderedCount];
    writeExecution(entry.command, entry.output, entry.status);
    renderedCount++;
  }
};

const cleanup = () => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  terminal?.dispose();
  terminal = null;
  fitAddon = null;
  renderedCount = 0;
};

watch(() => props.active, (active) => {
  if (active && !terminal) {
    initTerminal();
  } else if (active && terminal) {
    requestAnimationFrame(() => fitAddon?.fit());
  }
});

watch(() => props.history?.length, () => {
  nextTick(renderNewEntries);
});

onMounted(() => {
  if (props.active) {
    initTerminal();
  }
  renderNewEntries();
});

onBeforeUnmount(() => {
  cleanup();
});

defineExpose({ cleanup, writeExecution });
</script>

<style scoped>
.sandbox-terminal {
  background: #1e1e1e;
}
.sandbox-terminal :deep(.xterm) {
  padding: 4px;
  height: 100%;
}
.sandbox-terminal :deep(.xterm-viewport) {
  overflow-y: auto !important;
}
</style>
