'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function LogisticsTimelinePanel({ simulationId, getToken }) {
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (simulationId) {
      fetchLogisticsTimeline()
    }
  }, [simulationId])

  const fetchLogisticsTimeline = async () => {
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
      
      const response = await axios.get(
        `${API_BASE}/api/logistics/${simulationId}/timeline`,
        authConfig
      )
      
      setTimeline(response.data.timeline || [])
    } catch (err) {
      console.error('Failed to fetch logistics timeline:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch logistics timeline')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'DELIVERED':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'IN_TRANSIT':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      case 'DELAYED':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'LOST':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'PENDING':
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getRiskLevelColor = (riskLevel) => {
    switch (riskLevel) {
      case 'LOW':
        return 'bg-green-100 text-green-800'
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800'
      case 'HIGH':
        return 'bg-orange-100 text-orange-800'
      case 'CRITICAL':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (!simulationId) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Logistics Timeline</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No simulation ID provided</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Logistics Timeline</h3>
        <div className="text-center py-8 text-gray-500">Loading logistics timeline...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Logistics Timeline</h3>
        <div className="text-center py-8 text-gray-500">{error}</div>
        <button
          onClick={fetchLogisticsTimeline}
          className="mt-4 px-4 py-2 text-sm text-blue-600 hover:text-blue-800"
        >
          Retry
        </button>
      </div>
    )
  }

  if (timeline.length === 0) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Logistics Timeline</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No logistics information available yet.</p>
          <p className="text-sm mt-2">Logistics tracking will begin when shipment is booked during execution.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Logistics Timeline</h3>
        <button
          onClick={fetchLogisticsTimeline}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-6">
        {timeline.map((shipment) => {
          const conditionSnapshots = shipment.condition_snapshots || []
          
          return (
            <div key={shipment.id} className="border border-gray-200 rounded-lg p-4">
              {/* Shipment Header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="text-base font-semibold text-gray-900">Shipment</h4>
                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getStatusColor(shipment.status)}`}>
                      {shipment.status}
                    </span>
                  </div>
                  {shipment.tracking_number && (
                    <p className="text-sm text-gray-600">Tracking: <strong>{shipment.tracking_number}</strong></p>
                  )}
                  <p className="text-sm text-gray-600">
                    {shipment.origin_location} → {shipment.destination_location}
                  </p>
                  {shipment.carrier && (
                    <p className="text-xs text-gray-500 mt-1">Carrier: {shipment.carrier}</p>
                  )}
                </div>
              </div>

              {/* Shipment Timeline */}
              <div className="mb-4">
                <div className="flex items-center gap-4 text-xs text-gray-600">
                  {shipment.created_at && (
                    <span>Created: {new Date(shipment.created_at).toLocaleString()}</span>
                  )}
                  {shipment.estimated_delivery_date && (
                    <span>Est. Delivery: {new Date(shipment.estimated_delivery_date).toLocaleString()}</span>
                  )}
                  {shipment.actual_delivery_date && (
                    <span className="text-green-600 font-semibold">
                      Delivered: {new Date(shipment.actual_delivery_date).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>

              {/* Condition Snapshots */}
              {conditionSnapshots.length > 0 && (
                <div className="mt-4">
                  <h5 className="text-sm font-semibold text-gray-900 mb-3">Condition Snapshots</h5>
                  <div className="space-y-3">
                    {conditionSnapshots.map((snapshot, idx) => (
                      <div
                        key={snapshot.id || idx}
                        className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-gray-600">
                            {new Date(snapshot.timestamp).toLocaleString()}
                          </span>
                          <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getRiskLevelColor(snapshot.risk_level)}`}>
                            {snapshot.risk_level} RISK
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-4 gap-2 text-xs">
                          <div>
                            <span className="text-gray-600">Temperature:</span>
                            <span className="font-medium ml-1">{snapshot.temperature?.toFixed(1) || 'N/A'}°C</span>
                          </div>
                          <div>
                            <span className="text-gray-600">Humidity:</span>
                            <span className="font-medium ml-1">{snapshot.humidity?.toFixed(1) || 'N/A'}%</span>
                          </div>
                          <div>
                            <span className="text-gray-600">Shock Events:</span>
                            <span className="font-medium ml-1">{snapshot.shock_events || 0}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">Condition Score:</span>
                            <span className={`font-medium ml-1 ${
                              snapshot.condition_score >= 80 ? 'text-green-600' :
                              snapshot.condition_score >= 60 ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {snapshot.condition_score?.toFixed(1) || 'N/A'}/100
                            </span>
                          </div>
                        </div>
                        
                        {snapshot.notes && (
                          <p className="text-xs text-gray-600 mt-2">{snapshot.notes}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {conditionSnapshots.length === 0 && (
                <div className="text-center py-4 text-gray-500 text-sm">
                  No condition snapshots available yet.
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
