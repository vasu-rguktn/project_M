'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function DecisionTimeline({ simulationId, getToken }) {
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (simulationId) {
      fetchTimeline()
    }
  }, [simulationId])

  const fetchTimeline = async () => {
    if (!getToken || !simulationId) return
    
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
      
      // Fetch audit log entries for this simulation
      const response = await axios.get(
        `${API_BASE}/api/simulations/${simulationId}`,
        authConfig
      ).catch(() => ({ data: {} }))
      
      const simulation = response.data
      const events = []
      
      // Add creation event
      if (simulation.created_at) {
        events.push({
          type: 'CREATED',
          timestamp: simulation.created_at,
          description: 'Simulation created from AI recommendation'
        })
      }
      
      // Add approval event
      if (simulation.approved_at) {
        events.push({
          type: 'APPROVED',
          timestamp: simulation.approved_at,
          description: 'Simulation approved by user'
        })
      }
      
      // Add execution event
      if (simulation.executed_at) {
        events.push({
          type: 'EXECUTED',
          timestamp: simulation.executed_at,
          description: 'Simulation executed'
        })
      }
      
      // Sort by timestamp
      events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
      
      setTimeline(events)
    } catch (err) {
      console.error('Failed to fetch timeline:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch timeline')
    } finally {
      setLoading(false)
    }
  }

  const getEventColor = (type) => {
    switch (type) {
      case 'CREATED':
        return 'bg-blue-500'
      case 'APPROVED':
        return 'bg-green-500'
      case 'EXECUTED':
        return 'bg-purple-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getEventIcon = (type) => {
    switch (type) {
      case 'CREATED':
        return '📝'
      case 'APPROVED':
        return '✅'
      case 'EXECUTED':
        return '⚡'
      default:
        return '•'
    }
  }

  if (!simulationId) {
    return null
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Timeline</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Timeline</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  if (timeline.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Timeline</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No timeline events available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Timeline</h3>
      
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-300"></div>
        
        <div className="space-y-4">
          {timeline.map((event, index) => (
            <div key={index} className="relative flex items-start">
              {/* Event dot */}
              <div className={`relative z-10 w-8 h-8 rounded-full ${getEventColor(event.type)} flex items-center justify-center text-white text-sm`}>
                {getEventIcon(event.type)}
              </div>
              
              {/* Event content */}
              <div className="ml-4 flex-1">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">{event.type}</div>
                    <div className="text-xs text-gray-600 mt-1">{event.description}</div>
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(event.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
