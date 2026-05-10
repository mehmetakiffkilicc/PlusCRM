import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '../api/client'
import useAuthStore from '../stores/authStore'
import InlineSpinner from '../components/InlineSpinner'
import '../styles/Auth.css'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { login } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!email.trim()) {
      setError('Email adresi gereklidir')
      return
    }

    if (!password) {
      setError('Şifre gereklidir')
      return
    }

    if (password !== confirmPassword) {
      setError('Şifreler eşleşmiyor')
      return
    }

    if (password.length < 6) {
      setError('Şifre en az 6 karakter olmalı')
      return
    }

    setLoading(true)

    try {
      await apiClient.register(email, password)
      const response = await apiClient.login(email, password)
      login(response.user, response.token)
      navigate('/')
    } catch (err: any) {
      const status = err.response?.status
      const data = err.response?.data

      const isHtml = typeof data === 'string' && data.includes('<html')
      if (status === 405 && isHtml) {
        setError('API bağlantı hatası. Lütfen daha sonra tekrar deneyin.')
        return
      }

      if (data && typeof data === 'object') {
        // Django validation errors: { email: [...], non_field_errors: [...], ... }
        const messages: string[] = []
        for (const [key, val] of Object.entries(data)) {
          const fieldName = key === 'non_field_errors' ? '' : key === 'email' ? 'E-posta' : key === 'password' ? 'Şifre' : key
          const valStr = Array.isArray(val) ? (val as string[]).join(', ') : String(val)
          messages.push(fieldName ? `${fieldName}: ${valStr}` : valStr)
        }
        setError(messages.join(' '))
        return
      }

      if (data?.error) { setError(data.error); return }
      if (data?.detail) { setError(data.detail); return }
      if (err.message) { setError(`Kayıt başarısız: ${err.message}`); return }
      setError('Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-card">
          <h1> XPlusCRM</h1>
          <h2>Kayıt Ol</h2>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ornek@email.com"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Şifre</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Şifre Tekrar</label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            {error && <div className="error-message">{error}</div>}

            <button type="submit" className="btn btn-primary" disabled={loading}>
              <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                {loading && (
                  <InlineSpinner
                    size={16}
                    thickness={2}
                    color="#ffffff"
                    trackColor="rgba(255,255,255,0.35)"
                  />
                )}
                Kayıt Ol
              </span>
            </button>
          </form>

          <p className="auth-footer">
            Zaten hesabın var mı? <a href="/giris">Giriş Yap</a>
          </p>
        </div>
      </div>
    </div>
  )
}
