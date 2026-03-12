'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function StrategyReliabilityBadge({ strategyId, getToken }) {
  const [reliability, setReliability] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (strategyId) {
      fetchReliability()
    }
  }, [strategyId])

  const fetchReliability = async () => {
    if (!getToken || !strategyId) return
    
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
        `${API_BASE}/api/explainability/strategy-reliability/${strategyId}`,
        authConfig
      )
      
      setReliability(response.data)
    } catch (err) {
      console.error('Failed to fetch strategy reliability:', err)
      setReliability(null)
    } finally {
      setLoading(false)
    }
  }

  if (loading || !reliability || reliability.reliability_level === 'insufficient_data') {
    return null
  }

  const getReliabilityColor = () => {
    switch (reliability.reliability_level) {
      case 'high':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'low':
        return 'bg-red-100 text-red-800 border-red-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getReliabilityIcon = () => {
    switch (reliability.reliability_level) {
      case 'high':
        return '⭐'
      case 'medium':
        return '⚡'
      case 'low':
        return '⚠️'
      default:
        return '❓'
    }
  }

  return (
    <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold border ${getReliabilityColor()}`}>
      <span className="mr-1">{getReliabilityIcon()}</span>
      <span>{reliability.reliability_level.toUpperCase()} RELIABILITY</span>
      {reliability.reliability_score !== null && (
        <span className="ml-1 opacity-75">
          ({(reliability.reliability_score * 100).toFixed(0)}%)
        </span>
      )}
    </div>
  )
}
