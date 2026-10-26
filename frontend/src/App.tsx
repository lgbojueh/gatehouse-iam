import { FormEvent, useEffect, useState } from 'react'

type Me = { id: number; email: string; role: string; active: boolean }
type User = Me & { created_at: string }
type Audit = { id: number; event_type: string; target: string; detail: string; created_at: string }

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function App() {
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('Admin123!')
  const [token, setToken] = useState(localStorage.getItem('gatehouse_token') ?? '')
  const [me, setMe] = useState<Me | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [audit, setAudit] = useState<Audit[]>([])
  const [overview, setOverview] = useState<Record<string, string | number> | null>(null)
  const [error, setError] = useState('')

  useEffect(() => { if (token) loadDashboard(token) }, [token])

  async function request(path: string, authToken = token, init: RequestInit = {}) {
    const response = await fetch(`${API}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        ...(init.headers ?? {}),
      },
    })
    if (!response.ok) throw new Error((await response.json()).detail ?? 'Request failed')
    return response.json()
  }

  async function login(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const data = await request('/api/auth/login', '', { method: 'POST', body: JSON.stringify({ email, password }) })
      localStorage.setItem('gatehouse_token', data.access_token)
      setToken(data.access_token)
    } catch (err) { setError(err instanceof Error ? err.message : 'Login failed') }
  }

  async function loadDashboard(authToken: string) {
    setError('')
    try {
      const profile = await request('/api/me', authToken)
      setMe(profile)
      if (profile.role === 'analyst' || profile.role === 'admin') {
        setOverview(await request('/api/security/overview', authToken))
        setAudit(await request('/api/audit', authToken))
      }
      if (profile.role === 'admin') setUsers(await request('/api/admin/users', authToken))
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load dashboard') }
  }

  async function changeRole(user: User, role: string) {
    await request(`/api/admin/users/${user.id}/role`, token, { method: 'PATCH', body: JSON.stringify({ role }) })
    await loadDashboard(token)
  }

  function logout() {
    localStorage.removeItem('gatehouse_token')
    setToken(''); setMe(null); setUsers([]); setAudit([]); setOverview(null)
  }

  if (!token || !me) return (
    <main className="loginShell">
      <section className="brand"><div className="eyebrow">Identity • Authorization • Audit</div><h1>Gatehouse <span>IAM</span></h1><p>A security-focused identity platform demonstrating server-side RBAC and traceable privilege management.</p></section>
      <form className="loginCard" onSubmit={login}>
        <h2>Demo sign in</h2>
        <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        <button>Authenticate</button>
        <p className="hint">Try admin@example.com / Admin123!</p>
        {error && <p className="error">{error}</p>}
      </form>
    </main>
  )

  return (
    <main className="dashboard">
      <header><div><div className="eyebrow">Gatehouse IAM</div><h1>Security console</h1></div><div className="identity"><span>{me.email}</span><strong>{me.role}</strong><button onClick={logout}>Sign out</button></div></header>
      {error && <p className="error">{error}</p>}

      <section className="metrics">
        <Metric label="Current role" value={me.role} />
        {overview && <><Metric label="Active users" value={String(overview.active_users)} /><Metric label="Admins" value={String(overview.admins)} /><Metric label="Recent events" value={String(overview.recent_security_events)} /></>}
      </section>

      {me.role === 'admin' && <section className="panel"><div className="panelHead"><h2>Access management</h2><span>Admin only</span></div><div className="table">{users.map((user) => <div className="row" key={user.id}><div><strong>{user.email}</strong><small>User #{user.id}</small></div><select value={user.role} onChange={(e) => changeRole(user, e.target.value)}><option>user</option><option>analyst</option><option>admin</option></select></div>)}</div></section>}

      {(me.role === 'admin' || me.role === 'analyst') && <section className="panel"><div className="panelHead"><h2>Audit trail</h2><span>Analyst + Admin</span></div><div className="audit">{audit.slice(0, 12).map((event) => <article key={event.id}><strong>{event.event_type.replace('_', ' ')}</strong><span>{event.target}</span><p>{event.detail}</p><time>{new Date(event.created_at).toLocaleString()}</time></article>)}</div></section>}

      {me.role === 'user' && <section className="panel"><h2>Least privilege in action</h2><p>Your account can view its profile but is intentionally blocked from analyst and administrator endpoints. Sign in as another demo role to compare the authorization boundary.</p></section>}
    </main>
  )
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div> }
