import { useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { apiRequest } from './api'
import { Layout } from './components/Layout'
import { AlertsPage } from './pages/AlertsPage'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { SettingsPage } from './pages/SettingsPage'
import { TransactionDetailPage } from './pages/TransactionDetailPage'
import { TransactionsPage } from './pages/TransactionsPage'

const emptyMetrics = {
  total_transactions: 0,
  scored_transactions: 0,
  declined: 0,
  review: 0,
  approved: 0,
  average_risk_score: 0,
}

export default function App() {
  const navigate = useNavigate()
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [user, setUser] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [metrics, setMetrics] = useState(emptyMetrics)
  const [selectedId, setSelectedId] = useState(null)
  const [score, setScore] = useState(null)
  const [explanation, setExplanation] = useState(null)

  useEffect(() => {
    if (!token) return

    const load = async () => {
      const [me, txs, summary] = await Promise.all([
        apiRequest('/api/auth/me', {}, token),
        apiRequest('/api/transactions', {}, token),
        apiRequest('/api/metrics/summary', {}, token),
      ])
      setUser(me)
      setTransactions(txs)
      setMetrics(summary)
    }

    load().catch(() => {
      localStorage.removeItem('token')
      setToken(null)
    })
  }, [token])

  const selectedTransaction = useMemo(
    () => transactions.find((tx) => tx.id === selectedId),
    [transactions, selectedId],
  )

  useEffect(() => {
    if (!token || !selectedId) return
    Promise.all([
      apiRequest(`/api/scores/${selectedId}`, {}, token).catch(() => null),
      apiRequest(`/api/explanations/${selectedId}`, {}, token).catch(() => null),
    ]).then(([scoreData, explanationData]) => {
      setScore(scoreData)
      setExplanation(explanationData)
    })
  }, [selectedId, token])

  const onLogin = (newToken) => {
    localStorage.setItem('token', newToken)
    setToken(newToken)
  }

  const onLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  const onSelect = (id) => {
    setSelectedId(id)
    navigate('/transactions/detail')
  }

  if (!token) return <LoginPage onLogin={onLogin} />

  return (
    <Layout user={user} onLogout={onLogout}>
      <Routes>
        <Route path="/" element={<DashboardPage metrics={metrics} />} />
        <Route path="/transactions" element={<TransactionsPage transactions={transactions} onSelect={onSelect} />} />
        <Route path="/transactions/detail" element={<TransactionDetailPage transaction={selectedTransaction} score={score} explanation={explanation} />} />
        <Route path="/alerts" element={<AlertsPage transactions={transactions} onSelect={onSelect} />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
