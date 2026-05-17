import { create } from 'zustand'

let nextId = 1

export const useToasts = create((set, get) => ({
  toasts: [],

  /**
   * Push a toast.
   * @param {{message: string, kind?: 'info'|'success'|'warn'|'error', timeout?: number}} t
   */
  push(t) {
    const id = nextId++
    const toast = {
      id,
      kind: 'info',
      timeout: 4000,
      ...t,
    }
    set((s) => ({ toasts: [...s.toasts, toast] }))
    if (toast.timeout > 0) {
      setTimeout(() => get().dismiss(id), toast.timeout)
    }
    return id
  },

  dismiss(id) {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
  },
}))

export const toast = {
  info: (message, opts) => useToasts.getState().push({ ...opts, message, kind: 'info' }),
  success: (message, opts) => useToasts.getState().push({ ...opts, message, kind: 'success' }),
  warn: (message, opts) => useToasts.getState().push({ ...opts, message, kind: 'warn' }),
  error: (message, opts) => useToasts.getState().push({ ...opts, message, kind: 'error' }),
}
