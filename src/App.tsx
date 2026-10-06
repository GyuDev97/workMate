import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import type { ActionCard, ChatResponse, Dashboard, Task } from './types'

type Page = 'home' | 'assistant' | 'tasks' | 'activity'
const nav: { id: Page; icon: string; label: string }[] = [
  { id: 'home', icon: '⌂', label: '홈' }, { id: 'assistant', icon: '✦', label: 'Assistant' },
  { id: 'tasks', icon: '✓', label: '업무' }, { id: 'activity', icon: '◷', label: '활동 기록' }
]

function fmtTime(value: string) { return new Intl.DateTimeFormat('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value)) }
function fmtDate(value?: string) { return value ? new Intl.DateTimeFormat('ko-KR', { month: 'short', day: 'numeric' }).format(new Date(value)) : '기한 없음' }

function Logo() { return <div className="brand-mark"><span>✦</span></div> }
function StatusDot({ state }: { state: string }) { return <span className={`status-dot ${state}`} /> }

function PageHeader({ title, text, action }: { title: string; text: string; action?: React.ReactNode }) {
  return <header className="page-header"><div><p className="eyebrow">WORKMATE</p><h1>{title}</h1><p>{text}</p></div>{action}</header>
}

function Home({ data, move }: { data: Dashboard; move: (page: Page) => void }) {
  const openTasks = data.tasks.filter((task) => task.status !== 'DONE')
  const stats = [
    ['◷', '오늘 일정', data.events.length, 'calendar'], ['✓', '처리할 업무', openTasks.length, 'task'],
    ['✉', '중요 메일', data.mails.length, 'mail'], ['!', '확인 필요', data.mails.filter((mail) => mail.needs_reply).length, 'attention']
  ]
  return <>
    <PageHeader title={data.briefing.greeting} text={`${data.briefing.date_label} · 오늘의 업무를 정리했어요.`} />
    <section className="stat-grid">{stats.map(([icon, label, value, theme]) => <button className="stat-card" key={label as string} onClick={() => move(label === '처리할 업무' ? 'tasks' : label === '중요 메일' ? 'assistant' : 'home')}><span className={`stat-icon ${theme}`}>{icon}</span><span><b>{value}</b><small>{label}</small></span><i>›</i></button>)}</section>
    <section className="content-grid home-grid">
      <article className="panel schedule-panel"><div className="panel-head"><div><h2>오늘 일정</h2><p>집중해야 할 시간입니다.</p></div><button className="text-button" onClick={() => move('assistant')}>일정 물어보기</button></div>
        <div className="timeline">{data.events.map((event, index) => <div className="event" key={event.id}><time>{fmtTime(event.starts_at)}</time><span className={`event-line ${index === 0 ? 'now' : ''}`} /><div><strong>{event.title}</strong><p>{index === 0 ? '곧 시작 · 회의 준비' : event.ends_at ? `${fmtTime(event.starts_at)} – ${fmtTime(event.ends_at)}` : ''}</p></div></div>)}</div>
      </article>
      <article className="panel focus-panel"><div className="panel-head"><div><h2>우선 확인</h2><p>오늘 놓치지 말아야 할 항목입니다.</p></div></div>
        <ol className="priority-list">{data.briefing.priorities.map((priority, index) => <li key={priority}><em>{index + 1}</em><span>{priority}</span><button onClick={() => move('assistant')}>→</button></li>)}</ol>
      </article>
      <article className="panel mail-panel"><div className="panel-head"><div><h2>확인 필요 메일</h2><p>중요도와 회신 필요 여부로 정리했습니다.</p></div><button className="text-button" onClick={() => move('assistant')}>전체 보기</button></div>
        {data.mails.map((mail) => <button className="mail-row" key={mail.id} onClick={() => move('assistant')}><span className="avatar">{mail.sender.slice(0, 1)}</span><span className="mail-copy"><b>{mail.sender}</b><strong>{mail.subject}</strong><small>{mail.preview}</small></span>{mail.needs_reply && <span className="reply-pill">회신 필요</span>}</button>)}
      </article>
      <ProviderPanel providers={data.providers} />
    </section>
  </>
}

function ProviderPanel({ providers }: { providers: Dashboard['providers'] }) { return <article className="panel provider-panel"><div className="panel-head"><div><h2>시스템 상태</h2><p>연결 상태를 한눈에 확인합니다.</p></div></div>{providers.map((provider) => <div className="provider-row" key={provider.name}><span><StatusDot state={provider.state} />{provider.name}</span><small>{provider.detail}</small></div>)}</article> }

function ActionPreview({ action }: { action: ActionCard }) { return <div className="action-card"><div className="action-heading"><span>{action.kind === 'mail_draft' ? '✉' : '▣'}</span><div><b>{action.title}</b><small>실행 전 검토가 필요합니다.</small></div></div>{Object.entries(action.fields).map(([label, value]) => <div className="action-field" key={label}><small>{label}</small><p>{value}</p></div>)}<div className="action-buttons"><button className="secondary">수정</button><button className="primary" disabled>{action.kind === 'mail_draft' ? '검토 후 보내기' : '검토 후 실행'}</button></div></div> }

function Assistant({ data }: { data: Dashboard }) {
  const [messages, setMessages] = useState<{ role: 'assistant' | 'user'; text: string; action?: ActionCard; sources?: string[]; trace?: ChatResponse['trace'] }[]>([{ role: 'assistant', text: '안녕하세요. 오늘의 일정과 중요 메일을 확인해 두었어요. 무엇을 도와드릴까요?' }])
  const [input, setInput] = useState(''); const [loading, setLoading] = useState(false)
  async function submit(event: FormEvent) { event.preventDefault(); const message = input.trim(); if (!message || loading) return; setInput(''); setMessages((current) => [...current, { role: 'user', text: message }]); setLoading(true); try { const response: ChatResponse = await api.chat(message); setMessages((current) => [...current, { role: 'assistant', text: response.message, action: response.action, sources: response.sources, trace: response.trace }]) } catch (error) { setMessages((current) => [...current, { role: 'assistant', text: error instanceof Error ? `연결 오류: ${error.message}` : '요청을 처리하지 못했습니다.' }]) } finally { setLoading(false) } }
  const prompts = ['오늘 뭐 해야 돼?', '중요 메일 알려줘', '김대리에게 답장 써줘', '내일 일정 알려줘']
  return <><PageHeader title="Assistant" text="말로 요청하면 상황을 확인하고 필요한 작업을 준비합니다." /><section className="assistant-layout"><article className="panel conversation"><div className="conversation-head"><span><Logo /></span><div><b>workMate Assistant</b><small><StatusDot state="connected" />준비됨 · Tool Calling</small></div></div><div className="messages">{messages.map((message, index) => <div className={`message ${message.role}`} key={index}><div className="bubble">{message.text.split('\n').map((line, lineIndex) => <p key={lineIndex}>{line || <br />}</p>)}{message.action && <ActionPreview action={message.action} />}{message.trace?.length ? <small className="sources">{message.trace.map((trace) => `${trace.success ? '✓' : '!' } ${trace.tool}`).join(' · ')}</small> : null}{message.sources?.length ? <small className="sources">참조: {message.sources.join(' · ')}</small> : null}</div></div>)}{loading && <div className="message assistant"><div className="bubble typing"><i /><i /><i /></div></div>}</div><form className="composer" onSubmit={submit}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="workMate에게 요청하세요…" /><button className="send" type="submit" disabled={loading}>↑</button></form></article><aside className="assistant-side"><article className="panel compact"><h2>빠른 질문</h2><p>자주 쓰는 요청으로 바로 시작하세요.</p><div className="prompt-list">{prompts.map((prompt) => <button key={prompt} onClick={() => setInput(prompt)}>{prompt}<span>→</span></button>)}</div></article><article className="panel compact next-event"><p className="eyebrow">NEXT UP</p><h3>{data.events[0]?.title ?? '예정된 일정 없음'}</h3><b>{data.events[0] ? fmtTime(data.events[0].starts_at) : ''}</b><small>캘린더 Mock 데이터 기준</small></article></aside></section></>
}

function Tasks({ tasks, refresh }: { tasks: Task[]; refresh: () => Promise<void> }) {
  const [title, setTitle] = useState(''); const [priority, setPriority] = useState('MEDIUM'); const [saving, setSaving] = useState(false)
  async function add(event: FormEvent) { event.preventDefault(); if (!title.trim()) return; setSaving(true); try { await api.createTask(title.trim(), priority); setTitle(''); await refresh() } finally { setSaving(false) } }
  async function complete(id: string) { await api.completeTask(id); await refresh() }
  const open = tasks.filter((task) => task.status !== 'DONE'); const done = tasks.filter((task) => task.status === 'DONE')
  return <><PageHeader title="업무" text="일정과 구분하여, 완료할 일을 관리합니다." action={<span className="task-count">진행 중 <b>{open.length}</b></span>} /><section className="tasks-layout"><article className="panel task-list"><div className="panel-head"><div><h2>진행 중인 업무</h2><p>기한과 우선순위를 기준으로 정리했습니다.</p></div></div>{open.length ? open.map((task) => <TaskRow key={task.id} task={task} onComplete={complete} />) : <Empty text="진행 중인 업무가 없습니다." />}{done.length > 0 && <><h3 className="done-heading">완료됨</h3>{done.map((task) => <TaskRow key={task.id} task={task} onComplete={complete} />)}</>}</article><aside className="panel task-create"><h2>빠른 업무 추가</h2><p>대화 중 생성된 업무도 이곳에 모입니다.</p><form onSubmit={add}><label>업무 내용<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="예: API 문서 확인" /></label><label>우선순위<select value={priority} onChange={(event) => setPriority(event.target.value)}><option value="HIGH">높음</option><option value="MEDIUM">보통</option><option value="LOW">낮음</option></select></label><button className="primary full" disabled={saving}>{saving ? '추가 중…' : '업무 추가'}</button></form></aside></section></>
}

function TaskRow({ task, onComplete }: { task: Task; onComplete: (id: string) => void }) { const isDone = task.status === 'DONE'; return <div className={`task-row ${isDone ? 'done' : ''}`}><button className="check" onClick={() => !isDone && onComplete(task.id)} aria-label="완료 처리">{isDone ? '✓' : ''}</button><div><b>{task.title}</b>{task.description && <p>{task.description}</p>}<small>{fmtDate(task.due_at)} · {task.source === 'manual' ? '직접 추가' : task.source}</small></div><span className={`priority ${task.priority.toLowerCase()}`}>{task.priority === 'HIGH' ? '높음' : task.priority === 'MEDIUM' ? '보통' : '낮음'}</span></div> }
function Empty({ text }: { text: string }) { return <div className="empty">{text}</div> }

function Activity({ activities }: { activities: Dashboard['activities'] }) { return <><PageHeader title="활동 기록" text="workMate가 확인하거나 준비한 업무 흐름입니다." /><article className="panel activity-panel"><div className="panel-head"><div><h2>오늘</h2><p>민감한 메일 본문과 인증 정보는 기록하지 않습니다.</p></div></div>{activities.map((activity) => <div className="activity-row" key={activity.id}><time>{fmtTime(activity.occurred_at)}</time><span className={`activity-icon ${activity.category}`}>{activity.category === 'read' ? '◉' : '✦'}</span><div><b>{activity.action}</b><p>{activity.detail}</p></div></div>)}</article></> }

function Offline({ retry }: { retry: () => void }) { return <main className="offline"><Logo /><h1>Backend Offline</h1><p>workMate 백엔드에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인한 뒤 다시 시도해 주세요.</p><button className="primary" onClick={retry}>다시 연결</button><code>cd backend && python3 -m uvicorn server.main:app --port 8765</code></main> }

export default function App() {
  const [page, setPage] = useState<Page>('home'); const [data, setData] = useState<Dashboard | null>(null); const [offline, setOffline] = useState(false)
  const load = async () => { try { await api.health(); setData(await api.dashboard()); setOffline(false) } catch { setOffline(true) } }
  useEffect(() => {
    // Initial network synchronization intentionally begins after the renderer mounts.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load()
    window.workMate?.onNavigate((next) => setPage(next as Page))
  }, [])
  const content = useMemo(() => { if (!data) return null; if (page === 'assistant') return <Assistant data={data} />; if (page === 'tasks') return <Tasks tasks={data.tasks} refresh={load} />; if (page === 'activity') return <Activity activities={data.activities} />; return <Home data={data} move={setPage} /> }, [data, page])
  if (offline) return <Offline retry={() => void load()} />
  if (!data) return <div className="loading"><Logo /><span>workMate를 준비하는 중…</span></div>
  return <div className="app-shell"><aside className="sidebar"><div className="brand"><Logo /><div><b>workMate</b><small>개인 AI 업무 비서</small></div></div><nav>{nav.map((item) => <button className={page === item.id ? 'active' : ''} onClick={() => setPage(item.id)} key={item.id}><span>{item.icon}</span>{item.label}</button>)}</nav><div className="sidebar-bottom"><div className="privacy"><span>⌘</span><p><b>안전한 업무 처리</b><small>변경 작업은 항상 확인 후 실행</small></p></div><button className="settings">⚙ 설정 <span>›</span></button></div></aside><main className="main-content">{content}</main></div>
}
