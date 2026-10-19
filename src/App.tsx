import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import type { ActionCard, CalendarConnectionStatus, ChatResponse, Dashboard, KnowledgeArtifact, KnowledgeArtifactDetail, KnowledgeSource, Task } from './types'

type Page = 'home' | 'assistant' | 'tasks' | 'knowledge' | 'activity' | 'settings'
const nav: { id: Page; icon: string; label: string }[] = [
  { id: 'home', icon: '⌂', label: '홈' }, { id: 'assistant', icon: '✦', label: 'Assistant' },
  { id: 'tasks', icon: '✓', label: '업무' }, { id: 'knowledge', icon: '▤', label: '지식베이스' }, { id: 'activity', icon: '◷', label: '활동 기록' }
]

function fmtTime(value: string) { return new Intl.DateTimeFormat('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Seoul' }).format(new Date(value)) }
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

function ActionPreview({ action, onApprove, busy }: { action: ActionCard; onApprove: (action: ActionCard) => void; busy: boolean }) {
  const calendarAction = action.kind.startsWith('calendar_') && action.action_id
  const pending = action.status === 'pending_approval'
  const label = action.status === 'completed' ? '완료됨' : action.status === 'failed' ? '실패' : action.status === 'executing' ? '실행 중…' : action.kind === 'calendar_delete' ? '삭제' : '등록'
  return <div className="action-card"><div className="action-heading"><span>{action.kind === 'mail_draft' ? '✉' : '▣'}</span><div><b>{action.title}</b><small>{pending ? '실행 전 검토가 필요합니다.' : `상태: ${label}`}</small></div></div>{Object.entries(action.fields).map(([field, value]) => <div className="action-field" key={field}><small>{field}</small><p>{value}</p></div>)}<div className="action-buttons"><button className="secondary" disabled={!pending || busy}>취소</button><button className="primary" disabled={!calendarAction || !pending || busy} onClick={() => calendarAction && onApprove(action)}>{busy ? '실행 중…' : calendarAction ? label : '검토 후 보내기'}</button></div></div>
}

function Assistant({ data, refresh }: { data: Dashboard; refresh: () => Promise<void> }) {
  const [messages, setMessages] = useState<{ role: 'assistant' | 'user'; text: string; action?: ActionCard; sources?: string[]; trace?: ChatResponse['trace'] }[]>([{ role: 'assistant', text: '안녕하세요. 오늘의 일정과 중요 메일을 확인해 두었어요. 무엇을 도와드릴까요?' }])
  const [input, setInput] = useState(''); const [loading, setLoading] = useState(false); const [approving, setApproving] = useState<string | null>(null)
  async function submit(event: FormEvent) { event.preventDefault(); const message = input.trim(); if (!message || loading) return; setInput(''); setMessages((current) => [...current, { role: 'user', text: message }]); setLoading(true); try { const response: ChatResponse = await api.chat(message); setMessages((current) => [...current, { role: 'assistant', text: response.message, action: response.action, sources: response.sources, trace: response.trace }]) } catch (error) { setMessages((current) => [...current, { role: 'assistant', text: error instanceof Error ? `연결 오류: ${error.message}` : '요청을 처리하지 못했습니다.' }]) } finally { setLoading(false) } }
  async function approve(action: ActionCard) {
    if (!action.action_id || approving) return
    setApproving(action.action_id)
    try {
      const result = await api.approveAction(action.action_id)
      setMessages((current) => [...current.map((message) => message.action?.action_id === action.action_id ? { ...message, action: result.action } : message), { role: 'assistant', text: result.message }])
      await refresh()
    } finally { setApproving(null) }
  }
  const prompts = ['오늘 뭐 해야 돼?', '중요 메일 알려줘', '김대리에게 답장 써줘', '내일 일정 알려줘']
  const next = data.events.find((event) => new Date(event.starts_at).getTime() >= Date.now())
  return <><PageHeader title="Assistant" text="말로 요청하면 상황을 확인하고 필요한 작업을 준비합니다." /><section className="assistant-layout"><article className="panel conversation"><div className="conversation-head"><span><Logo /></span><div><b>workMate Assistant</b><small><StatusDot state="connected" />준비됨 · Tool Calling</small></div></div><div className="messages">{messages.map((message, index) => <div className={`message ${message.role}`} key={index}><div className="bubble">{message.text.split('\n').map((line, lineIndex) => <p key={lineIndex}>{line || <br />}</p>)}{message.action && <ActionPreview action={message.action} onApprove={(current) => void approve(current)} busy={approving === message.action.action_id} />}{message.trace?.length ? <small className="sources">{message.trace.map((trace) => `${trace.success ? '✓' : '!' } ${trace.tool}`).join(' · ')}</small> : null}{message.sources?.length ? <small className="sources">참조: {message.sources.join(' · ')}</small> : null}</div></div>)}{loading && <div className="message assistant"><div className="bubble typing"><i /><i /><i /></div></div>}</div><form className="composer" onSubmit={submit}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="workMate에게 요청하세요…" /><button className="send" type="submit" disabled={loading}>↑</button></form></article><aside className="assistant-side"><article className="panel compact"><h2>빠른 질문</h2><p>자주 쓰는 요청으로 바로 시작하세요.</p><div className="prompt-list">{prompts.map((prompt) => <button key={prompt} onClick={() => setInput(prompt)}>{prompt}<span>→</span></button>)}</div></article><article className="panel compact next-event"><p className="eyebrow">NEXT UP</p><h3>{next?.title ?? '다음 일정이 없습니다.'}</h3><b>{next ? fmtTime(next.starts_at) : ''}</b><small>{next ? 'Calendar Provider 기준' : '예정된 일정 없음'}</small></article></aside></section></>
}

function Settings({ refresh }: { refresh: () => Promise<void> }) {
  const [status, setStatus] = useState<CalendarConnectionStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [notice, setNotice] = useState('')
  useEffect(() => { void api.calendarStatus().then(setStatus).catch(() => setNotice('연결 상태를 확인하지 못했습니다.')) }, [])
  async function run(action: 'connect' | 'verify' | 'disconnect') {
    setLoading(true); setNotice('')
    try {
      const result = action === 'connect' ? await api.connectCalendar() : action === 'verify' ? await api.verifyCalendar() : await api.disconnectCalendar()
      setStatus(result)
      setNotice(action === 'connect' ? 'Google Calendar 연결을 완료했습니다.' : action === 'verify' ? '연결을 확인했습니다.' : '이 기기의 연결 토큰을 제거했습니다.')
      await refresh()
    } catch (error) { setNotice(error instanceof Error ? error.message : '요청을 처리하지 못했습니다.') } finally { setLoading(false) }
  }
  const connected = status?.state === 'connected'
  return <><PageHeader title="설정" text="Google Calendar 연결과 권한 상태를 관리합니다." /><section className="settings-layout"><article className="panel settings-panel"><div className="panel-head"><div><h2>Google Calendar</h2><p>일정 조회와 승인된 일정 변경에 사용됩니다.</p></div><StatusDot state={status?.state ?? 'offline'} /></div><div className="connection-status"><b>{connected ? '연결됨' : status?.state === 'mock' ? 'Mock 모드' : '연결되지 않음'}</b><small>{status?.detail ?? '상태를 불러오는 중입니다.'}</small><small>Calendar ID: {status?.calendar_id ?? 'primary'}</small></div><div className="action-buttons settings-actions">{connected ? <><button className="secondary" disabled={loading} onClick={() => void run('verify')}>연결 확인</button><button className="primary danger" disabled={loading} onClick={() => void run('disconnect')}>연결 해제</button></> : <button className="primary" disabled={loading || status?.provider === 'mock'} onClick={() => void run('connect')}>{loading ? '브라우저 인증 대기 중…' : 'Google 계정 연결'}</button>}</div>{status?.provider === 'mock' && <p className="settings-hint">`.env`에서 `WORKMATE_CALENDAR_PROVIDER=google`으로 바꾸고 OAuth Desktop Client JSON 경로를 설정하면 실제 계정을 연결할 수 있습니다.</p>}{notice && <p className="settings-notice">{notice}</p>}</article></section></>
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

function KnowledgeBase() {
  const [sources, setSources] = useState<KnowledgeSource[]>([]); const [selected, setSelected] = useState<KnowledgeSource | null>(null)
  const [artifacts, setArtifacts] = useState<KnowledgeArtifact[]>([]); const [document, setDocument] = useState<KnowledgeArtifactDetail | null>(null)
  const [name, setName] = useState(''); const [path, setPath] = useState(''); const [notice, setNotice] = useState(''); const [busy, setBusy] = useState(false); const [runId, setRunId] = useState<string | null>(null)
  const loadSources = async () => { const next = await api.knowledgeSources(); setSources(next); if (selected) setSelected(next.find((source) => source.id === selected.id) ?? null) }
  const select = async (source: KnowledgeSource) => { setSelected(source); setDocument(null); setNotice(''); setArtifacts(await api.knowledgeArtifacts(source.id)) }
  useEffect(() => { void loadSources().catch((error) => setNotice(error instanceof Error ? error.message : '지식베이스를 불러오지 못했습니다.')) }, [])
  async function register(event: FormEvent) { event.preventDefault(); if (!name.trim() || !path.trim()) return; setBusy(true); setNotice(''); try { const source = await api.createKnowledgeSource(name.trim(), path.trim()); setName(''); setPath(''); await loadSources(); await select(source); setNotice('폴더를 등록했습니다. 수집 버튼으로 문서를 읽어 오세요.') } catch (error) { setNotice(error instanceof Error ? error.message : '폴더를 등록하지 못했습니다.') } finally { setBusy(false) } }
  async function scan() { if (!selected) return; setBusy(true); setNotice('수집 대상을 확인하는 중입니다…'); try { const run = await api.scanKnowledgeSource(selected.id); setRunId(run.id); const poll = async () => { const current = await api.knowledgeSyncRun(run.id); if (current.status === 'running') { if (!current.total) setNotice('수집 대상을 확인하는 중입니다…'); else { const percent = Math.round((current.scanned / current.total) * 100); setNotice(`수집 중: ${current.scanned} / ${current.total}개 파일 (${percent}%)`) }; window.setTimeout(() => void poll(), 1000); return }; setBusy(false); setRunId(null); await loadSources(); await select(selected); setNotice(current.status === 'cancelled' ? `수집을 중단했습니다. ${current.scanned} / ${current.total}개 파일 처리됨` : `수집 완료: ${current.scanned}개 확인 · ${current.parsed}개 파싱 · ${current.chunks_created}개 청크`) }; void poll() } catch (error) { setNotice(error instanceof Error ? error.message : '수집에 실패했습니다.'); setBusy(false) } }
  async function cancel() { if (!runId) return; await api.cancelKnowledgeSyncRun(runId); setNotice('중단 요청을 보냈습니다. 현재 파일 처리가 끝나면 멈춥니다.') }
  async function open(artifact: KnowledgeArtifact) { try { setDocument(await api.knowledgeArtifact(artifact.id)) } catch (error) { setNotice(error instanceof Error ? error.message : '문서를 열 수 없습니다.') } }
  return <><PageHeader title="지식베이스" text="로컬 폴더의 문서를 안전하게 수집하고 원문을 확인합니다." /><section className="knowledge-layout"><aside className="panel source-panel"><h2>지식 폴더</h2><p>등록한 폴더만 읽습니다. 원본 파일은 변경하지 않습니다.</p><form className="source-form" onSubmit={register}><input value={name} onChange={(event) => setName(event.target.value)} placeholder="표시 이름 (예: 업무 문서)" /><input value={path} onChange={(event) => setPath(event.target.value)} placeholder="로컬 폴더 경로" /><button className="primary full" disabled={busy}>{busy ? '처리 중…' : '폴더 등록'}</button></form><div className="source-list">{sources.map((source) => <button key={source.id} className={selected?.id === source.id ? 'selected' : ''} onClick={() => void select(source)}><b>{source.name}</b><small>{source.artifact_count}개 문서 · {source.last_synced_at ? '수집됨' : '미수집'}</small></button>)}</div></aside><article className="panel archive-panel"><div className="panel-head"><div><h2>{selected?.name ?? '폴더를 선택하세요'}</h2><p>{selected ? selected.local_path : '왼쪽에서 폴더를 등록하면 수집할 수 있습니다.'}</p></div>{selected && <div className="action-buttons">{runId && <button className="secondary" onClick={() => void cancel()}>수집 중단</button>}<button className="primary" disabled={busy} onClick={() => void scan()}>{busy ? '수집 중…' : '수집·파싱'}</button></div>}</div>{notice && <p className="knowledge-notice">{notice}</p>}{selected && (artifacts.length ? <div className="artifact-list">{artifacts.map((artifact) => <button key={artifact.id} className={document?.id === artifact.id ? 'selected' : ''} onClick={() => void open(artifact)}><span>▤</span><div><b>{artifact.title}</b><small>{artifact.relative_path} · {artifact.chunk_count ? `${artifact.chunk_count}개 청크` : '추출 실패 또는 미파싱'}</small></div></button>)}</div> : <Empty text="아직 수집된 문서가 없습니다." />)}</article>{document && <article className="panel document-panel"><div className="panel-head"><div><h2>{document.title}</h2><p>{document.relative_path} · {document.chunk_count}개 청크</p></div></div><pre>{document.content || '추출된 텍스트가 없습니다.'}</pre></article>}</section></>
}

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
  const content = useMemo(() => { if (!data) return null; if (page === 'assistant') return <Assistant data={data} refresh={load} />; if (page === 'tasks') return <Tasks tasks={data.tasks} refresh={load} />; if (page === 'knowledge') return <KnowledgeBase />; if (page === 'activity') return <Activity activities={data.activities} />; if (page === 'settings') return <Settings refresh={load} />; return <Home data={data} move={setPage} /> }, [data, page])
  if (offline) return <Offline retry={() => void load()} />
  if (!data) return <div className="loading"><Logo /><span>workMate를 준비하는 중…</span></div>
  return <div className="app-shell"><aside className="sidebar"><div className="brand"><Logo /><div><b>workMate</b><small>개인 AI 업무 비서</small></div></div><nav>{nav.map((item) => <button className={page === item.id ? 'active' : ''} onClick={() => setPage(item.id)} key={item.id}><span>{item.icon}</span>{item.label}</button>)}</nav><div className="sidebar-bottom"><div className="privacy"><span>⌘</span><p><b>안전한 업무 처리</b><small>변경 작업은 항상 확인 후 실행</small></p></div><button className={`settings ${page === 'settings' ? 'active' : ''}`} onClick={() => setPage('settings')}>⚙ 설정 <span>›</span></button></div></aside><main className="main-content">{content}</main></div>
}
