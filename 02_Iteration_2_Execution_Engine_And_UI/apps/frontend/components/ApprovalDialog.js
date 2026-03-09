'use client'

import { useState } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function ApprovalDialog({ 
  simulation, 
  isOpen, 
  onClose, 
  getToken, 
  onApproved,
  onRejected 
}) {
  const [loading, setLoading] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')
  const [error, setError] = useState(null)
  const [action, setAction] = useState(null) // 'approve' or 'reject'

  if (!isOpen || !simulation) return null

  const handleApprove = async () => {
    if (!getToken) return
    
    setLoading(true)
    setError(null)
    setAction('approve')
    
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
        `${API_BASE}/api/simulations/approve`,
        { simulation_id: simulation.id },
        authConfig
      )
      
      if (onApproved) {
        onApproved(response.data)
      }
      
      onClose()
    } catch (err) {
      console.error('Failed to approve simulation:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to approve simulation')
    } finally {
      setLoading(false)
      setAction(null)
    }
  }

  const handleReject = async () => {
    if (!getToken) return
    
    setLoading(true)
    setError(null)
    setAction('reject')
    
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
        `${API_BASE}/api/simulations/reject`,
        { 
          simulation_id: simulation.id,
          reason: rejectionReason || 'No reason provided'
        },
        authConfig
      )
      
      if (onRejected) {
        onRejected(response.data)
      }
      
      onClose()
    } catch (err) {
      console.error('Failed to reject simulation:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to reject simulation')
    } finally {
      setLoading(false)
      setAction(null)
    }
  }

  const handleClose = () => {
    setRejectionReason('')
    setError(null)
    setAction(null)
    onClose()
  }

  return (
    <div className="fixed inset-0 backdrop-blur-[2px] bg-black/20 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Approve Simulation</h2>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600"
              disabled={loading}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{simulation.asset_name || 'Asset'}</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-500">Action</div>
                <div className="font-semibold">{simulation.action}</div>
              </div>
              <div>
                <div className="text-gray-500">Quantity</div>
                <div className="font-semibold">{simulation.quantity}</div>
              </div>
              {simulation.expected_roi !== null && (
                <div>
                  <div className="text-gray-500">Expected ROI</div>
                  <div className="font-semibold">{simulation.expected_roi.toFixed(1)}%</div>
                </div>
              )}
              {simulation.risk_score !== null && (
                <div>
                  <div className="text-gray-500">Risk Score</div>
                  <div className="font-semibold">{(simulation.risk_score * 100).toFixed(0)}%</div>
                </div>
              )}
            </div>
          </div>

          {simulation.simulation_result && (
            <div className="mb-4 p-3 bg-gray-50 rounded-md">
              <h4 className="text-sm font-semibold text-gray-900 mb-2">Projected Impact</h4>
              {simulation.simulation_result.projected_roi !== null && (
                <div className="text-sm text-gray-700 mb-1">
                  Projected ROI: <span className="font-semibold">{simulation.simulation_result.projected_roi.toFixed(2)}%</span>
                </div>
              )}
              {simulation.simulation_result.warnings && simulation.simulation_result.warnings.length > 0 && (
                <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                  <div className="font-semibold mb-1">Warnings:</div>
                  <ul className="list-disc list-inside">
                    {simulation.simulation_result.warnings.map((warning, idx) => (
                      <li key={idx}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rejection Reason (if rejecting)
            </label>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Optional reason for rejection"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 placeholder-gray-400"
              rows="3"
            />
          </div>

          <div className="flex justify-end gap-3">
            <button
              onClick={handleReject}
              disabled={loading}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
            >
              {loading && action === 'reject' ? 'Rejecting...' : 'Reject'}
            </button>
            <button
              onClick={handleApprove}
              disabled={loading}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {loading && action === 'approve' ? 'Approving...' : 'Approve'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
