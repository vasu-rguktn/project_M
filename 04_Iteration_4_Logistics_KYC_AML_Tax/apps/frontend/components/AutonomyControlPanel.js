'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function AutonomyControlPanel({ getToken }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [enabling, setEnabling] = useState(false)
  const [disabling, setDisabling] = useState(false)
  const [showEnableConfirm, setShowEnableConfirm] = useState(false)

  useEffect(() => {
    fetchStatus()
  }, [])

  const fetchStatus = async () => {
    if (!getToken) return
    
    setLoading(true)
    setError(null)
    
    try {
      const token = await getToken()
      
      if (!token || !token.trim()) {
        throw new Error('No authentication token available')
      }
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const response = await axios.get(
        `${API_BASE}/api/autonomy/status`,
        authConfig
      )
      
      setStatus(response.data)
    } catch (err) {
      console.error('Failed to fetch autonomy status:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch status')
    } finally {
      setLoading(false)
    }
  }

  const handleEnable = async () => {
    if (!getToken || !showEnableConfirm) return
    
    setEnabling(true)
    setError(null)
    
    try {
      const token = await getToken()
      
      if (!token || !token.trim()) {
        throw new Error('No authentication token available')
      }
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const response = await axios.post(
        `${API_BASE}/api/autonomy/enable`,
        {
          policy_name: 'default_policy',
          max_daily_trades: 1,  // Hard limit
          confidence_threshold: 0.85,  // Hard limit
          risk_threshold: 0.30  // Hard limit
        },
        authConfig
      )
      
      setShowEnableConfirm(false)
      await fetchStatus()
      alert('Autonomy enabled with strict limits:\n- Max 1 trade per day\n- Confidence >= 85%\n- Risk <= 30%')
    } catch (err) {
      console.error('Failed to enable autonomy:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to enable autonomy'
      
      // Handle kill switch error specifically
      if (err.response?.status === 403 && errorMessage.includes('kill switch')) {
        setError('Autonomy is disabled by kill switch. Please contact an administrator to enable autonomy.')
      } else {
        setError(errorMessage)
      }
    } finally {
      setEnabling(false)
    }
  }

  const handleDisable = async () => {
    if (!getToken) return
    
    const confirmed = window.confirm(
      'Are you sure you want to DISABLE autonomy?\n\n' +
      'This will activate the kill switch and immediately halt all autonomous execution.'
    )
    
    if (!confirmed) return
    
    setDisabling(true)
    setError(null)
    
    try {
      const token = await getToken()
      
      if (!token || !token.trim()) {
        throw new Error('No authentication token available')
      }
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const response = await axios.post(
        `${API_BASE}/api/autonomy/disable`,
        { reason: 'Disabled by user via UI' },
        authConfig
      )
      
      await fetchStatus()
      alert('Autonomy DISABLED. Kill switch activated.')
    } catch (err) {
      console.error('Failed to disable autonomy:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to disable autonomy')
    } finally {
      setDisabling(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Autonomy Control Panel</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Autonomy Control Panel</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  const isKillSwitchActive = status?.kill_switch_active || false
  const isAutonomyEnabled = status?.autonomy_enabled || false

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Autonomy Control Panel</h3>
        <button
          onClick={fetchStatus}
          className="text-sm text-blue-600 hover:text-blue-800"
          disabled={enabling || disabling}
        >
          Refresh
        </button>
      </div>

      {/* Kill Switch Status */}
      <div className={`mb-4 p-4 rounded-lg border-2 ${
        isKillSwitchActive 
          ? 'bg-red-50 border-red-300' 
          : 'bg-green-50 border-green-300'
      }`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold mb-1">
              {isKillSwitchActive ? '🔴 Kill Switch: ACTIVE' : '🟢 Kill Switch: INACTIVE'}
            </div>
            <div className="text-xs text-gray-600">
              {isKillSwitchActive 
                ? 'All autonomous execution is disabled'
                : 'Autonomous execution may proceed if policy allows'}
            </div>
          </div>
          {isKillSwitchActive ? (
            <button
              onClick={() => setShowEnableConfirm(true)}
              disabled={enabling || disabling}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
            >
              Enable Autonomy
            </button>
          ) : (
            <button
              onClick={handleDisable}
              disabled={enabling || disabling}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 text-sm font-medium"
            >
              {disabling ? 'Disabling...' : 'Disable Autonomy'}
            </button>
          )}
        </div>
      </div>

      {/* Enable Confirmation Dialog */}
      {showEnableConfirm && (
        <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-sm font-semibold text-yellow-900 mb-2">
            ⚠️ Enable Guarded Autonomy?
          </div>
          <div className="text-xs text-yellow-800 mb-3">
            <p className="mb-1"><strong>Strict Limits:</strong></p>
            <ul className="list-disc list-inside space-y-1">
              <li>Maximum 1 trade per day</li>
              <li>Confidence &gt;= 85% required</li>
              <li>Risk &lt;= 30% required</li>
              <li>All actions are logged and auditable</li>
            </ul>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleEnable}
              disabled={enabling}
              className="px-3 py-1 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50 text-sm"
            >
              {enabling ? 'Enabling...' : 'Confirm Enable'}
            </button>
            <button
              onClick={() => setShowEnableConfirm(false)}
              disabled={enabling}
              className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Current Limits */}
      {status && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Current Limits</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="p-2 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">Trades Today</div>
              <div className="text-lg font-semibold">
                {status.total_trades_today} / {status.active_policies[0]?.max_daily_trades || 1}
              </div>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <div className="text-xs text-gray-500">Value Today</div>
              <div className="text-lg font-semibold">
                ₹{status.total_value_today.toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Active Policies */}
      {status?.active_policies && status.active_policies.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Active Policies</h4>
          {status.active_policies.map((policy) => (
            <div key={policy.id} className="p-3 bg-gray-50 rounded mb-2">
              <div className="text-sm font-medium text-gray-700 mb-1">{policy.policy_name}</div>
              <div className="text-xs text-gray-600 space-y-1">
                <div>Confidence Threshold: ≥{policy.confidence_threshold * 100}%</div>
                <div>Risk Threshold: ≤{policy.risk_threshold * 100}%</div>
                <div>Max Daily Trades: {policy.max_daily_trades}</div>
                {policy.max_trade_value > 0 && (
                  <div>Max Trade Value: ₹{policy.max_trade_value.toFixed(2)}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}
    </div>
  )
}
