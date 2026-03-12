'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function ConfidenceStabilityIndicator({ getToken, days = 30 }) {
  const [drift, setDrift] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchConfidenceDrift()
  }, [days])

  const fetchConfidenceDrift = async () => {
    if (!getToken) return
    
    setLoading(true)
    
    try {
      const token = await getToken()
      if (!token || !token.trim()) return
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const response = await axios.get(
        `${API_BASE}/api/explainability/confidence-drift?days=${days}`,
        authConfig
      )
      
      setDrift(response.data)
    } catch (err) {
      console.error('Failed to fetch confidence drift:', err)
      setDrift(null)
    } finally {
      setLoading(false)
    }
  }

  if (loading || !drift) {
    return null
  }

  if (drift.sample_size < 2) {
    return (
      <div className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-600">
        <span className="mr-1">📊</span>
        Insufficient data
      </div>
    )
  }

  const getTrendColor = () => {
    switch (drift.confidence_trend) {
      case 'increasing':
        return 'text-green-600 bg-green-50'
      case 'decreasing':
        return 'text-red-600 bg-red-50'
      case 'stable':
        return 'text-blue-600 bg-blue-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getTrendIcon = () => {
    switch (drift.confidence_trend) {
      case 'increasing':
        return '📈'
      case 'decreasing':
        return '📉'
      case 'stable':
        return '➡️'
      default:
        return '📊'
    }
  }

  const getStabilityLevel = () => {
    if (!drift.volatility) return 'unknown'
    if (drift.volatility < 0.1) return 'high'
    if (drift.volatility < 0.2) return 'medium'
    return 'low'
  }

  const stabilityLevel = getStabilityLevel()

  return (
    <div className="inline-flex items-center gap-2">
      <div className={`inline-flex items-center px-2 py-1 rounded text-xs ${getTrendColor()}`}>
        <span className="mr-1">{getTrendIcon()}</span>
        <span className="font-medium">{drift.confidence_trend}</span>
      </div>
      <div className="text-xs text-gray-600">
        Stability: <span className="font-medium">{stabilityLevel}</span>
      </div>
      {drift.average_confidence !== null && (
        <div className="text-xs text-gray-600">
          Avg: <span className="font-medium">{(drift.average_confidence * 100).toFixed(1)}%</span>
        </div>
      )}
    </div>
  )
}
