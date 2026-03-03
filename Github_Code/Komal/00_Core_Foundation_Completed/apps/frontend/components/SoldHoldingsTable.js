import { useState, useEffect } from 'react'
import { useAuth, useUser } from '@clerk/nextjs'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function SoldHoldingsTable({ getToken: propGetToken, onRefresh }) {
  const [soldHoldings, setSoldHoldings] = useState([])
  const [profitSummary, setProfitSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const { getToken: hookGetToken } = useAuth()
  const { isLoaded, user } = useUser()
  
  // Use prop getToken if provided, otherwise use hook
  const getToken = propGetToken || hookGetToken

  useEffect(() => {
    // Only fetch when Clerk is loaded and user is authenticated
    if (isLoaded && user && getToken) {
      fetchSoldHoldings()
    } else if (isLoaded && !user) {
      // User not authenticated, stop loading
      setLoading(false)
    }
  }, [isLoaded, user, getToken, onRefresh])

  const fetchSoldHoldings = async () => {
    // Ensure Clerk is loaded and user is authenticated
    if (!isLoaded || !user || !getToken) {
      setLoading(false)
      return
    }
    
    try {
      setLoading(true)
      const token = await getToken()
      
      if (!token || !token.trim()) {
        console.warn('No authentication token available for sold holdings')
        setLoading(false)
        setSoldHoldings([])
        setProfitSummary(null)
        return
      }
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const [soldRes, profitRes] = await Promise.allSettled([
        axios.get(`${API_BASE}/api/holdings/sold`, authConfig),
        axios.get(`${API_BASE}/api/holdings/realized-profit`, authConfig)
      ])
      
      // Handle sold holdings response
      if (soldRes.status === 'fulfilled') {
        setSoldHoldings(soldRes.value.data || [])
      } else {
        // Check if it's a 401 error
        if (soldRes.reason?.response?.status === 401) {
          console.warn('Authentication failed for sold holdings - token may be expired')
          setSoldHoldings([])
        } else {
          console.warn('Failed to fetch sold holdings:', soldRes.reason?.message || 'Unknown error')
          setSoldHoldings([])
        }
      }
      
      // Handle profit summary response
      if (profitRes.status === 'fulfilled') {
        setProfitSummary(profitRes.value.data)
      } else {
        // Check if it's a 401 error
        if (profitRes.reason?.response?.status === 401) {
          console.warn('Authentication failed for profit summary - token may be expired')
          setProfitSummary(null)
        } else {
          console.warn('Failed to fetch profit summary:', profitRes.reason?.message || 'Unknown error')
          setProfitSummary(null)
        }
      }
    } catch (err) {
      console.error('Unexpected error fetching sold holdings:', err)
      // Set empty state on any unexpected error
      setSoldHoldings([])
      setProfitSummary(null)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-4 text-gray-600">Loading sold holdings...</p>
      </div>
    )
  }

  if (!soldHoldings || soldHoldings.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        <p className="text-lg mb-2">No sold holdings yet</p>
        <p className="text-sm">Your sold holdings and realized profits will appear here</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Profit Summary */}
      {profitSummary && (
        <div className="px-6 py-4 bg-gradient-to-r from-green-50 to-blue-50 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Realized Profit Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-gray-500">Total Sales</div>
              <div className="text-lg font-bold text-gray-900">{profitSummary.total_sales}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Total Realized Profit</div>
              <div className={`text-lg font-bold ${profitSummary.total_realized_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ₹{profitSummary.total_realized_profit.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Average ROI</div>
              <div className={`text-lg font-bold ${profitSummary.average_roi >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {profitSummary.average_roi.toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Total Quantity Sold</div>
              <div className="text-lg font-bold text-gray-900">{profitSummary.total_quantity_sold}</div>
            </div>
          </div>
        </div>
      )}

      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Sold Holdings History</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Wine
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Quantity Sold
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Buy Price
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sell Price
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Realized Profit
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ROI
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sold Date
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {soldHoldings.map((sold) => (
              <tr key={sold.event_id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {sold.asset_name}
                  </div>
                  <div className="text-sm text-gray-500">{sold.vintage} • {sold.region}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{sold.quantity_sold}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">₹{sold.buy_price.toFixed(2)}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">₹{sold.sell_price.toFixed(2)}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className={`text-sm font-medium ${
                    sold.realized_profit >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {sold.realized_profit >= 0 ? '+' : ''}₹{sold.realized_profit.toFixed(2)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className={`text-sm font-medium ${
                    sold.realized_roi >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {sold.realized_roi >= 0 ? '+' : ''}{sold.realized_roi.toFixed(2)}%
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-500">
                    {new Date(sold.sold_at).toLocaleDateString()}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

