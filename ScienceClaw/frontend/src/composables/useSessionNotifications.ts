import { ref, onUnmounted } from 'vue'
import { subscribeSessionNotifications } from '../api/agent'

type NotificationCallback = (data: {
  session_id: string;
  source?: string;
  timestamp: number;
  session_event?: { event: string; data: any };
}) => void

const onSessionCreatedCallbacks = ref<Map<number, NotificationCallback>>(new Map())
const onSessionUpdatedCallbacks = ref<Map<number, NotificationCallback>>(new Map())

let cancelFn: (() => void) | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let nextCallbackId = 0
let connectionActive = false

function handleEvent({ event, data }: { event: string; data: any }) {
  if (event === 'session_created') {
    onSessionCreatedCallbacks.value.forEach(cb => cb(data))
  } else if (event === 'session_updated') {
    onSessionUpdatedCallbacks.value.forEach(cb => cb(data))
  }
}

async function connect() {
  if (cancelFn) return
  connectionActive = true
  try {
    cancelFn = await subscribeSessionNotifications({
      onMessage: handleEvent,
      onClose: () => {
        cancelFn = null
        if (connectionActive) {
          reconnectTimer = setTimeout(() => connect(), 3000)
        }
      },
      onError: () => {
        cancelFn = null
        if (connectionActive) {
          reconnectTimer = setTimeout(() => connect(), 5000)
        }
      },
    })
  } catch {
    cancelFn = null
    if (connectionActive) {
      reconnectTimer = setTimeout(() => connect(), 5000)
    }
  }
}

function disconnect() {
  connectionActive = false
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (cancelFn) {
    cancelFn()
    cancelFn = null
  }
}

function ensureConnected() {
  if (!cancelFn && connectionActive) {
    connect()
  }
}

export function useSessionNotifications() {
  const callbackIds: number[] = []

  const onSessionCreated = (cb: NotificationCallback) => {
    const id = nextCallbackId++
    onSessionCreatedCallbacks.value.set(id, cb)
    callbackIds.push(id)
    if (!connectionActive) connect()
    else ensureConnected()
  }

  const onSessionUpdated = (cb: NotificationCallback) => {
    const id = nextCallbackId++
    onSessionUpdatedCallbacks.value.set(id, cb)
    callbackIds.push(id)
    if (!connectionActive) connect()
    else ensureConnected()
  }

  onUnmounted(() => {
    for (const id of callbackIds) {
      onSessionCreatedCallbacks.value.delete(id)
      onSessionUpdatedCallbacks.value.delete(id)
    }
    const totalCallbacks = onSessionCreatedCallbacks.value.size + onSessionUpdatedCallbacks.value.size
    if (totalCallbacks === 0) {
      disconnect()
    }
  })

  return { onSessionCreated, onSessionUpdated }
}
