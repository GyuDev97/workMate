export type Priority = 'HIGH' | 'MEDIUM' | 'LOW'
export type TaskStatus = 'TODO' | 'IN_PROGRESS' | 'DONE' | 'CANCELLED'

export interface Event { id: string; title: string; starts_at: string; ends_at?: string; description: string; all_day: boolean; location: string; calendar_id: string; source: string }
export interface Mail { id: string; sender: string; subject: string; received_at: string; needs_reply: boolean; preview: string }
export interface Task { id: string; title: string; description: string; priority: Priority; due_at?: string; status: TaskStatus; source: string; created_at: string }
export interface Provider { name: string; state: 'connected' | 'mock' | 'offline'; detail: string }
export interface Activity { id: string; occurred_at: string; action: string; detail: string; category: string }
export interface Dashboard {
  briefing: { greeting: string; date_label: string; overview: string[]; priorities: string[] }
  events: Event[]; mails: Mail[]; tasks: Task[]; providers: Provider[]; activities: Activity[]
}
export type ApprovalStatus = 'not_required' | 'pending_approval' | 'executing' | 'completed' | 'failed'
export interface ActionCard { action_id?: string; kind: 'mail_draft' | 'calendar_event' | 'calendar_update' | 'calendar_delete' | 'task'; title: string; fields: Record<string, string>; requires_confirmation: boolean; status: ApprovalStatus }
export interface CalendarConnectionStatus { provider: 'mock' | 'google'; state: 'connected' | 'mock' | 'offline'; detail: string; calendar_id: string }
export interface ActionExecutionResult { action: ActionCard; message: string }
export interface ToolTrace { tool: string; risk: 'READ' | 'WRITE_LOCAL' | 'PROPOSED_EXTERNAL_WRITE'; success: boolean; duration_ms: number }
export interface ChatResponse { message: string; sources: string[]; action?: ActionCard; trace: ToolTrace[] }
