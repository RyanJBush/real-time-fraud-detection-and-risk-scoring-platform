import { useState } from 'react'
import { apiRequest } from '../api'

export function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('analyst@meridian.ai')
  const [password, setPassword] = useState('password123')
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    try {
      const data = await apiRequest('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      onLogin(data.access_token)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <form className="w-full max-w-sm rounded-lg border bg-white p-6 shadow-sm" onSubmit={submit}>
        <h2 className="mb-4 text-xl font-semibold">Sign in</h2>
        <div className="mb-3">
          <label className="mb-1 block text-sm">Email</label>
          <input className="w-full rounded border px-3 py-2" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="mb-3">
          <label className="mb-1 block text-sm">Password</label>
          <input type="password" className="w-full rounded border px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        <button className="w-full rounded bg-slate-900 px-3 py-2 text-white" type="submit">
          Login
        </button>
      </form>
    </div>
  )
}
