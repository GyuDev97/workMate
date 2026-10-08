import type { ActionExecutionResult, CalendarConnectionStatus, ChatResponse, Dashboard, Task } from './types'

const baseUrl = import.meta.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8765'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) {
    const problem = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(problem?.detail ?? (response.status === 0 ? 'Backend Offline' : `요청 처리에 실패했습니다 (${response.status}).`))
  }
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string; service: string }>('/health'),
  dashboard: () => request<Dashboard>('/api/v1/dashboard'),
  chat: (message: string) => request<ChatResponse>('/api/v1/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  createTask: (title: string, priority: string) => request<Task>('/api/v1/tasks', { method: 'POST', body: JSON.stringify({ title, priority }) }),
  completeTask: (id: string) => request<Task>(`/api/v1/tasks/${id}/complete`, { method: 'POST' }),
  calendarStatus: () => request<CalendarConnectionStatus>('/api/v1/calendar/status'),
  connectCalendar: () => request<CalendarConnectionStatus>('/api/v1/calendar/connect', { method: 'POST' }),
  verifyCalendar: () => request<CalendarConnectionStatus>('/api/v1/calendar/verify', { method: 'POST' }),
  disconnectCalendar: () => request<CalendarConnectionStatus>('/api/v1/calendar/disconnect', { method: 'POST' }),
  approveAction: (id: string) => request<ActionExecutionResult>(`/api/v1/actions/${id}/approve`, { method: 'POST' })
}
