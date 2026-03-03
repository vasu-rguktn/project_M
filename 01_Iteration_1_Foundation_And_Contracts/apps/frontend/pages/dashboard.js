import { useEffect, useState } from 'react'
import { useUser, useAuth } from '@clerk/nextjs'
import axios from 'axios'
import NavBar from '../components/NavBar'
import PortfolioCard from '../components/PortfolioCard'
import PortfolioTrendChart from '../components/PortfolioTrendChart'
import HoldingsTable from '../components/HoldingsTable'
import SoldHoldingsTable from '../components/SoldHoldingsTable'
import MarketPulseCard from '../components/MarketPulseCard'
import ArbitrageCard from '../components/ArbitrageCard'
import AlertCard from '../components/AlertCard'
import WatchlistCard from '../components/WatchlistCard'
import AdvisorCard from '../components/AdvisorCard'
import SimulationHistoryTable from '../components/SimulationHistoryTable'
import OutcomeHistoryTable from '../components/OutcomeHistoryTable'
import PerformanceMetricsPanel from '../components/PerformanceMetricsPanel'
import LearningInsightsPanel from '../components/LearningInsightsPanel'
import AutonomyControlPanel from '../components/AutonomyControlPanel'
import AutonomousExecutionPanel from '../components/AutonomousExecutionPanel'
import ExecutionHistoryTable from '../components/ExecutionHistoryTable'
import CapitalSummaryPanel from '../components/CapitalSummaryPanel'
import StrategyPerformancePanel from '../components/StrategyPerformancePanel'
import DecisionReplayPanel from '../components/DecisionReplayPanel'
import DecisionTimeline from '../components/DecisionTimeline'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

// Add axios interceptor for better error handling
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.warn('Authentication error (401): Token may be expired or invalid')
    }
    return Promise.reject(error)
  }
)

export default function Dashboard() {
  const [portfolioSummary, setPortfolioSummary] = useState(null)
  const [holdings, setHoldings] = useState([])
  const [marketPulse, setMarketPulse] = useState({})
  const [arbitrage, setArbitrage] = useState([])
  const [alerts, setAlerts] = useState([])
  const [trendData, setTrendData] = useState([])
  const [watchlist, setWatchlist] = useState([])
  const [agentProposals, setAgentProposals] = useState([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState(null)
  const [refreshingAlerts, setRefreshingAlerts] = useState(false)
  const [runningAgent, setRunningAgent] = useState(false)
  const [agentError, setAgentError] = useState(null)
  const [agentProgress, setAgentProgress] = useState('')
  const { isLoaded, user } = useUser()
  const { getToken } = useAuth()

  // Function to fetch alerts only
  const fetchAlerts = async () => {
    if (!isLoaded || !user || !getToken) return
    
    try {
      const token = await getToken()
      if (!token) return
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const response = await axios.get(`${API_BASE}/api/alerts?limit=10`, authConfig)
      const alertsData = response.data || []
      setAlerts(alertsData)
      if (alertsData.length > 0) {
        console.log(`✅ Fetched ${alertsData.length} alerts`)
      } else {
        console.log('ℹ️ No alerts found (user may not have watchlisted/owned assets with alerts)')
      }
    } catch (err) {
      console.warn('⚠️ Failed to fetch alerts:', err.response?.status || err.message)
      // Don't show error, just log it
    }
  }

  // Auto-refresh alerts every 30 seconds
  useEffect(() => {
    if (!isLoaded || !user) return
    
    // Initial fetch
    fetchAlerts()
    
    // Set up interval for auto-refresh
    const interval = setInterval(() => {
      fetchAlerts()
    }, 30000) // 30 seconds
    
    return () => clearInterval(interval)
  }, [isLoaded, user, getToken])

  const fetchDashboardData = async () => {
    // Don't proceed if Clerk is not loaded or user is not authenticated
    if (!isLoaded || !user) {
      setLoading(false)
      return
    }
    
    try {
      setLoading(true)
      setApiError(null)
      
      // Get Clerk session token for authentication
      const token = await getToken()
      
      if (!token) {
        console.error('No authentication token available')
        setApiError('Authentication token not available. Please sign in again.')
        setLoading(false)
        return
      }
      
      // Create axios config with Authorization header
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      // Fetch all dashboard data with authentication
      const results = await Promise.allSettled([
        axios.get(`${API_BASE}/api/portfolio/summary`, authConfig),
        axios.get(`${API_BASE}/api/portfolio/holdings`, authConfig),
        axios.get(`${API_BASE}/api/market/pulse`, authConfig),
        axios.get(`${API_BASE}/api/arbitrage?limit=5`, authConfig),
        axios.get(`${API_BASE}/api/alerts?limit=5`, authConfig),
        axios.get(`${API_BASE}/api/portfolio/trend?days=30`, authConfig),
        axios.get(`${API_BASE}/api/watchlist`, authConfig),
        axios.get(`${API_BASE}/api/agent/proposals?limit=10`, authConfig)
      ])
      
      const [summaryRes, holdingsRes, pulseRes, arbitrageRes, alertsRes, trendRes, watchlistRes, proposalsRes] = results
      
      // Portfolio Summary
      if (summaryRes.status === 'fulfilled') {
        setPortfolioSummary(summaryRes.value.data)
      } else {
        console.warn('Failed to fetch portfolio summary:', summaryRes.reason?.response?.status || summaryRes.reason?.message)
        setPortfolioSummary(null)
      }
      
      // Holdings - use new active holdings endpoint
      try {
        const holdingsActiveRes = await axios.get(`${API_BASE}/api/holdings/active`, authConfig)
        setHoldings(holdingsActiveRes.data || [])
      } catch (err) {
        if (holdingsRes.status === 'fulfilled') {
          setHoldings(holdingsRes.value.data || [])
        } else {
          console.warn('Failed to fetch holdings:', err.response?.status || err.message)
          setHoldings([])
        }
      }
      
      // Market Pulse
      if (pulseRes.status === 'fulfilled') {
        setMarketPulse(pulseRes.value.data || {})
      } else {
        console.warn('Failed to fetch market pulse:', pulseRes.reason?.response?.status || pulseRes.reason?.message)
        setMarketPulse({})
      }
      
      // Arbitrage Opportunities
      if (arbitrageRes.status === 'fulfilled') {
        setArbitrage(arbitrageRes.value.data || [])
      } else {
        console.warn('Failed to fetch arbitrage opportunities:', arbitrageRes.reason?.response?.status || arbitrageRes.reason?.message)
        setArbitrage([])
      }
      
      // Alerts
      if (alertsRes.status === 'fulfilled') {
        const alertsData = alertsRes.value.data || []
        setAlerts(alertsData)
      } else {
        console.warn('Failed to fetch alerts:', alertsRes.reason?.response?.status || alertsRes.reason?.message)
        setAlerts([])
      }
      
      // Portfolio Trend
      if (trendRes.status === 'fulfilled') {
        setTrendData(trendRes.value.data || [])
      } else {
        console.warn('Failed to fetch portfolio trend:', trendRes.reason?.response?.status || trendRes.reason?.message)
        setTrendData([])
      }
      
      // Watchlist
      if (watchlistRes.status === 'fulfilled') {
        setWatchlist(watchlistRes.value.data?.items || [])
      } else {
        console.warn('Failed to fetch watchlist:', watchlistRes.reason?.response?.status || watchlistRes.reason?.message)
        setWatchlist([])
      }
      
      // Agent Proposals
      if (proposalsRes && proposalsRes.status === 'fulfilled') {
        setAgentProposals(proposalsRes.value.data || [])
      } else {
        console.warn('Failed to fetch agent proposals:', proposalsRes?.reason?.response?.status || proposalsRes?.reason?.message)
        setAgentProposals([])
      }
    } catch (err) {
      console.error('Critical error fetching dashboard data:', err)
      if (err.response?.status === 401) {
        setApiError('Authentication failed. Please sign out and sign in again.')
      } else if (err.response?.status === 403) {
        setApiError('Access forbidden. Please check your permissions.')
      } else if (!err.response) {
        setApiError('Cannot connect to backend. Make sure the backend is running on http://localhost:4000')
      } else {
        console.warn('Non-critical error:', err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isLoaded && user) {
      fetchDashboardData()
    }
  }, [isLoaded, user, getToken])

  // Auto-refresh portfolio data every 30 seconds
  useEffect(() => {
    if (!isLoaded || !user) return
    
    const interval = setInterval(async () => {
      try {
        const token = await getToken()
        if (!token) return
        
        const authConfig = {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
        
        const timestamp = new Date().getTime()
        const [summaryRes, holdingsRes, trendRes] = await Promise.allSettled([
          axios.get(`${API_BASE}/api/portfolio/summary`, authConfig),
          axios.get(`${API_BASE}/api/holdings/active`, authConfig),
          axios.get(`${API_BASE}/api/portfolio/trend?days=30&_t=${timestamp}`, authConfig)
        ])
        
        if (summaryRes.status === 'fulfilled') {
          setPortfolioSummary(summaryRes.value.data)
        }
        if (holdingsRes.status === 'fulfilled') {
          setHoldings(holdingsRes.value.data || [])
        }
        if (trendRes.status === 'fulfilled') {
          setTrendData(trendRes.value.data || [])
        }
      } catch (err) {
        console.warn('Auto-refresh failed:', err)
      }
    }, 30000) // 30 seconds
    
    return () => clearInterval(interval)
  }, [isLoaded, user, getToken])

  // Centralized function to refresh watchlist from backend
  const refreshWatchlist = async () => {
    if (!isLoaded || !user || !getToken) return
    
    try {
      const token = await getToken()
      if (!token) return
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const watchlistRes = await axios.get(`${API_BASE}/api/watchlist`, authConfig)
      setWatchlist(watchlistRes.data?.items || [])
    } catch (err) {
      console.error('Failed to refresh watchlist:', err)
      // Don't show error, just log it
    }
  }

  const handleWatchlistRemove = async (assetId) => {
    try {
      const token = await getToken()
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      await axios.delete(`${API_BASE}/api/watchlist/remove`, {
        ...authConfig,
        data: { asset_id: assetId }
      })
      
      // Refresh watchlist from backend to ensure consistency
      await refreshWatchlist()
    } catch (err) {
      console.error('Failed to remove from watchlist:', err)
      alert('Failed to remove from watchlist. Please try again.')
    }
  }

  const handleWatchlistToggle = async (assetId) => {
    try {
      const token = await getToken()
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      // Check current status
      const checkRes = await axios.get(`${API_BASE}/api/watchlist/check/${assetId}`, authConfig)
      const isCurrentlyInWatchlist = checkRes.data?.in_watchlist || false
      
      if (isCurrentlyInWatchlist) {
        // Remove from watchlist
        await axios.delete(`${API_BASE}/api/watchlist/remove`, {
          ...authConfig,
          data: { asset_id: assetId }
        })
      } else {
        // Add to watchlist
        await axios.post(`${API_BASE}/api/watchlist/add`, 
          { asset_id: assetId },
          authConfig
        )
      }
      
      // Always refresh watchlist after toggle to ensure UI is in sync
      await refreshWatchlist()
    } catch (err) {
      console.error('Failed to toggle watchlist:', err)
      if (err.response?.status !== 400 && err.response?.status !== 404) {
        alert('Failed to update watchlist. Please try again.')
      }
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <NavBar />
      <main className="max-w-7xl mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome{user ? `, ${user.firstName || user.emailAddresses[0]?.emailAddress || ''}` : ''}
          </h1>
          <p className="text-gray-600">Your wine trading intelligence dashboard</p>
        </div>

        {apiError && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg">
            <p className="font-semibold">Connection Error</p>
            <p className="text-sm mt-1">{apiError}</p>
            <p className="text-sm mt-2">Make sure the backend is running: <code className="bg-red-100 px-2 py-1 rounded">cd apps/backend && python start.py</code></p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading dashboard data...</p>
          </div>
        ) : (
          <>
            {/* Portfolio Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <PortfolioCard 
                title="Total Portfolio Value" 
                value={portfolioSummary ? `₹${portfolioSummary.total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '₹0.00'}
                change={portfolioSummary?.today_change}
                changePercent={portfolioSummary?.change_percent}
                subtitle={`${portfolioSummary?.bottles || 0} bottles across ${portfolioSummary?.regions?.split(',').length || 0} regions`}
              />
              <PortfolioCard 
                title="Today's Change" 
                value={portfolioSummary ? `₹${Math.abs(portfolioSummary.today_change).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '₹0.00'}
                change={portfolioSummary?.today_change}
                changePercent={portfolioSummary?.change_percent}
                subtitle="24 hour performance"
              />
              <PortfolioCard 
                title="Average ROI" 
                value={portfolioSummary ? `${portfolioSummary.avg_roi.toFixed(2)}%` : '0.00%'}
                subtitle="Across all holdings"
              />
            </div>

            {/* Portfolio Trend Chart */}
            <div className="bg-white rounded-lg shadow-sm p-6 mb-8 border border-gray-100">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Portfolio Trend (30 Days)</h3>
                <button
                  onClick={async () => {
                    try {
                      const token = await getToken()
                      const authConfig = {
                        headers: {
                          'Authorization': `Bearer ${token}`,
                          'Content-Type': 'application/json'
                        }
                      }
                      const timestamp = new Date().getTime()
                      const trendRes = await axios.get(`${API_BASE}/api/portfolio/trend?days=30&_t=${timestamp}`, authConfig)
                      setTrendData(trendRes.data || [])
                    } catch (err) {
                      console.error('Failed to refresh trend:', err)
                    }
                  }}
                  className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  title="Refresh trend data"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Refresh
                </button>
              </div>
              {trendData.length > 0 ? (
                <PortfolioTrendChart data={trendData} />
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p className="text-sm mb-2">No historical data available yet.</p>
                  <p className="text-xs">Portfolio snapshots will appear here after transactions.</p>
                </div>
              )}
            </div>

            {/* Market Pulse */}
            {Object.keys(marketPulse).length > 0 && (
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Market Pulse by Region</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
                  {Object.entries(marketPulse).map(([region, change]) => (
                    <MarketPulseCard key={region} region={region} change={change} />
                  ))}
                </div>
              </div>
            )}

            {/* Holdings Table */}
            <div className="mb-8">
              <HoldingsTable 
                holdings={holdings} 
                onWatchlistToggle={handleWatchlistToggle} 
                getToken={getToken} 
                watchlist={watchlist}
                onHoldingsUpdate={async () => {
                  // Refresh holdings, portfolio summary, and trend after sell
                  // Add small delay to ensure backend snapshot is created
                  await new Promise(resolve => setTimeout(resolve, 500))
                  
                  const token = await getToken()
                  const authConfig = {
                    headers: {
                      'Authorization': `Bearer ${token}`,
                      'Content-Type': 'application/json'
                    }
                  }
                  
                  // Force refresh trend by adding timestamp to bypass cache
                  const timestamp = new Date().getTime()
                  const [holdingsRes, summaryRes, trendRes] = await Promise.allSettled([
                    axios.get(`${API_BASE}/api/holdings/active`, authConfig),
                    axios.get(`${API_BASE}/api/portfolio/summary`, authConfig),
                    axios.get(`${API_BASE}/api/portfolio/trend?days=30&_t=${timestamp}`, authConfig)
                  ])
                  if (holdingsRes.status === 'fulfilled') {
                    setHoldings(holdingsRes.value.data || [])
                  }
                  if (summaryRes.status === 'fulfilled') {
                    setPortfolioSummary(summaryRes.value.data)
                  }
                  if (trendRes.status === 'fulfilled') {
                    setTrendData(trendRes.value.data || [])
                  }
                }}
              />
            </div>

            {/* Sold Holdings & Realized Profits */}
            <div className="mb-8">
              <SoldHoldingsTable 
                getToken={getToken}
                onRefresh={async () => {
                  // Refresh all data when sold holdings refresh
                  await fetchDashboardData()
                }}
              />
            </div>

            {/* Watchlist */}
            <div className="mb-8">
              <WatchlistCard 
                watchlist={watchlist} 
                onRemove={handleWatchlistRemove}
                getToken={getToken}
              />
            </div>

            {/* Arbitrage Opportunities and Alerts Side by Side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Arbitrage Opportunities */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Arbitrage Opportunities</h3>
                <div className="space-y-4">
                  {arbitrage.length > 0 ? (
                    arbitrage.map((opp, idx) => (
                      <ArbitrageCard 
                        key={idx} 
                        opportunity={{
                          ...opp,
                          onBuySuccess: async () => {
                            // Refresh holdings, portfolio, and trend after buy
                            // Add small delay to ensure backend snapshot is created
                            await new Promise(resolve => setTimeout(resolve, 500))
                            
                            const token = await getToken()
                            const authConfig = {
                              headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                              }
                            }
                            
                            // Force refresh trend by adding timestamp
                            const timestamp = new Date().getTime()
                            const [holdingsRes, summaryRes, trendRes] = await Promise.allSettled([
                              axios.get(`${API_BASE}/api/holdings/active`, authConfig),
                              axios.get(`${API_BASE}/api/portfolio/summary`, authConfig),
                              axios.get(`${API_BASE}/api/portfolio/trend?days=30&_t=${timestamp}`, authConfig)
                            ])
                            if (holdingsRes.status === 'fulfilled') {
                              setHoldings(holdingsRes.value.data || [])
                            }
                            if (summaryRes.status === 'fulfilled') {
                              setPortfolioSummary(summaryRes.value.data)
                            }
                            if (trendRes.status === 'fulfilled') {
                              setTrendData(trendRes.value.data || [])
                            }
                          }
                        }}
                        onWatchlistToggle={handleWatchlistToggle}
                        getToken={getToken}
                        isInWatchlist={watchlist.some(w => w.asset_id === opp.asset_id)}
                      />
                    ))
                  ) : (
                    <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                      No arbitrage opportunities at this time
                    </div>
                  )}
                </div>
              </div>

              {/* Alerts */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Recent Alerts</h3>
                  <button
                    onClick={async () => {
                      setRefreshingAlerts(true)
                      await fetchAlerts()
                      setRefreshingAlerts(false)
                    }}
                    disabled={refreshingAlerts}
                    className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50 flex items-center gap-1"
                    title="Refresh alerts"
                  >
                    <svg 
                      className={`w-4 h-4 ${refreshingAlerts ? 'animate-spin' : ''}`} 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {refreshingAlerts ? 'Refreshing...' : 'Refresh'}
                  </button>
                </div>
                <div className="space-y-4">
                  {alerts.length > 0 ? (
                    alerts.map((alert) => (
                      <AlertCard 
                        key={alert.id} 
                        alert={alert} 
                        getToken={getToken}
                        onMarkRead={(alertId) => {
                          setAlerts(alerts.map(a => a.id === alertId ? {...a, read: true} : a))
                        }}
                      />
                    ))
                  ) : (
                    <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                      No alerts at this time
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Agent Proposals / Advisor Recommendations */}
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">AI Advisor Recommendations</h3>
                <button
                  onClick={async () => {
                    if (!getToken || runningAgent) return
                    
                    setRunningAgent(true)
                    setAgentError(null)
                    setAgentProgress('Starting analysis...')
                    
                    try {
                      const token = await getToken()
                      const authConfig = {
                        headers: {
                          'Authorization': `Bearer ${token}`,
                          'Content-Type': 'application/json'
                        }
                      }
                      
                      // Show progress updates
                      const progressInterval = setInterval(() => {
                        setAgentProgress(prev => {
                          if (prev === 'Starting analysis...') return 'Fetching portfolio data...'
                          if (prev === 'Fetching portfolio data...') return 'Analyzing market trends...'
                          if (prev === 'Analyzing market trends...') return 'Evaluating opportunities...'
                          if (prev === 'Evaluating opportunities...') return 'Generating recommendations...'
                          return 'Finalizing analysis...'
                        })
                      }, 5000) // Update every 5 seconds
                      
                      // Trigger agent analysis with timeout
                      const runRes = await axios.post(
                        `${API_BASE}/api/agent/run`,
                        { asset_id: null },
                        {
                          ...authConfig,
                          timeout: 90000  // 90 seconds timeout (frontend timeout should be longer than backend)
                        }
                      )
                      
                      clearInterval(progressInterval)
                      setAgentProgress('')
                      
                      if (runRes.data.success) {
                        setAgentProgress('Saving results...')
                        // Show recommendation from response immediately (even if DB save failed)
                        if (runRes.data.results?.recommendation) {
                          const rec = runRes.data.results.recommendation
                          if (rec && rec.asset_id) {
                            const tempProposal = {
                              proposal_id: runRes.data.run_id || `temp_${Date.now()}`,
                              asset_id: rec.asset_id,
                              asset_name: rec.asset_id.replace('asset_', 'Asset '),
                              recommendation: rec.action || 'HOLD',
                              confidence_score: runRes.data.results.confidence_score || 0.5,
                              expected_roi: rec.expected_roi,
                              rationale: rec.rationale || runRes.data.results.explanation || '',
                              compliance_status: runRes.data.results.compliance_status || 'PENDING'
                            }
                            setAgentProposals([tempProposal])
                          }
                        }
                        // Refresh proposals from database after agent run
                        await new Promise(resolve => setTimeout(resolve, 2000))
                        try {
                          const proposalsRes = await axios.get(`${API_BASE}/api/agent/proposals?limit=10`, authConfig)
                          if (proposalsRes.data && proposalsRes.data.length > 0) {
                            setAgentProposals(proposalsRes.data)
                          }
                        } catch (fetchErr) {
                          console.warn('Failed to fetch proposals from database:', fetchErr)
                          // Keep the temp proposal we created above
                        }
                        setAgentProgress('')
                      } else {
                        setAgentError(runRes.data.error || 'Agent analysis failed')
                        setAgentProgress('')
                      }
                    } catch (err) {
                      console.error('Failed to run agent:', err)
                      // Check for timeout errors (both frontend and backend timeouts)
                      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout') || err.response?.data?.error?.includes('timed out')) {
                        const timeoutMsg = err.response?.data?.error || 'Agent analysis timed out. The analysis may be taking longer than expected. Please try again or check if the backend is running properly.'
                        setAgentError(timeoutMsg)
                      } else if (err.response?.status === 400) {
                        // Handle validation errors
                        setAgentError(err.response?.data?.error || err.response?.data?.detail || 'Invalid request. Please check your input.')
                      } else if (err.response?.status === 500) {
                        setAgentError(err.response?.data?.error || err.response?.data?.detail || 'Server error during agent execution. Check backend logs.')
                      } else {
                        setAgentError(err.response?.data?.error || err.message || 'Failed to run agent analysis. Make sure the backend is running.')
                      }
                      setAgentProgress('')
                    } finally {
                      setRunningAgent(false)
                    }
                  }}
                  disabled={runningAgent}
                  className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium flex items-center gap-2"
                >
                  {runningAgent ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {agentProgress || 'Analyzing...'}
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      Run AI Analysis
                    </>
                  )}
                </button>
              </div>
              
              {agentError && (
                <div className="mb-4 bg-red-50 border border-red-200 text-red-800 p-3 rounded-lg text-sm">
                  <strong>Error:</strong> {agentError}
                </div>
              )}
              
              {agentProposals.length > 0 ? (
                <div className="space-y-4">
                  {agentProposals.map((proposal) => (
                    <AdvisorCard
                      key={proposal.proposal_id}
                      proposal={proposal}
                      getToken={getToken}
                      onAction={async (action, proposalId) => {
                        // Refresh holdings, portfolio, and trend after action
                        await new Promise(resolve => setTimeout(resolve, 500))
                        
                        const token = await getToken()
                        const authConfig = {
                          headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                          }
                        }
                        
                        const timestamp = new Date().getTime()
                        const [holdingsRes, summaryRes, trendRes, proposalsRes] = await Promise.allSettled([
                          axios.get(`${API_BASE}/api/holdings/active`, authConfig),
                          axios.get(`${API_BASE}/api/portfolio/summary`, authConfig),
                          axios.get(`${API_BASE}/api/portfolio/trend?days=30&_t=${timestamp}`, authConfig),
                          axios.get(`${API_BASE}/api/agent/proposals?limit=10`, authConfig)
                        ])
                        if (holdingsRes.status === 'fulfilled') {
                          setHoldings(holdingsRes.value.data || [])
                        }
                        if (summaryRes.status === 'fulfilled') {
                          setPortfolioSummary(summaryRes.value.data)
                        }
                        if (trendRes.status === 'fulfilled') {
                          setTrendData(trendRes.value.data || [])
                        }
                        if (proposalsRes.status === 'fulfilled') {
                          setAgentProposals(proposalsRes.value.data || [])
                        }
                      }}
                    />
                  ))}
                </div>
              ) : (
                <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                  <p className="mb-2">No AI recommendations yet</p>
                  <p className="text-sm">Click "Run AI Analysis" to get personalized trading recommendations</p>
                </div>
              )}
            </div>

            {/* Phase 11: Simulation History */}
            <div className="mb-8">
              <SimulationHistoryTable 
                getToken={getToken}
                onSimulationUpdate={async () => {
                  // Refresh data after simulation update
                  await new Promise(resolve => setTimeout(resolve, 500))
                  const token = await getToken()
                  const authConfig = {
                    headers: {
                      'Authorization': `Bearer ${token}`,
                      'Content-Type': 'application/json'
                    }
                  }
                  const [holdingsRes, summaryRes, trendRes] = await Promise.allSettled([
                    axios.get(`${API_BASE}/api/holdings/active`, authConfig),
                    axios.get(`${API_BASE}/api/portfolio/summary`, authConfig),
                    axios.get(`${API_BASE}/api/portfolio/trend?days=30`, authConfig)
                  ])
                  if (holdingsRes.status === 'fulfilled') {
                    setHoldings(holdingsRes.value.data || [])
                  }
                  if (summaryRes.status === 'fulfilled') {
                    setPortfolioSummary(summaryRes.value.data)
                  }
                  if (trendRes.status === 'fulfilled') {
                    setTrendData(trendRes.value.data || [])
                  }
                }}
              />
            </div>

            {/* Phase 20: Portfolio & Capital Engine */}
            <div className="mb-8">
              <CapitalSummaryPanel getToken={getToken} />
            </div>

            {/* Phase 12: Outcome Tracking & Performance Metrics */}
            <div className="mb-8">
              <PerformanceMetricsPanel getToken={getToken} />
            </div>

            <div className="mb-8">
              <OutcomeHistoryTable getToken={getToken} />
            </div>

            {/* Phase 21: Strategy Performance */}
            <div className="mb-8">
              <StrategyPerformancePanel getToken={getToken} />
            </div>

            {/* Phase 13: Learning Insights */}
            <div className="mb-8">
              <LearningInsightsPanel getToken={getToken} />
            </div>

            {/* Phase 14: Autonomy Control Panel */}
            <div className="mb-8">
              <AutonomyControlPanel getToken={getToken} />
            </div>

            {/* Phase 16: Autonomous Execution Engine */}
            <div className="mb-8">
              <AutonomousExecutionPanel getToken={getToken} />
            </div>

            <div className="mb-8">
              <ExecutionHistoryTable getToken={getToken} />
            </div>

            {/* Phase 24: UX Trust & Explainability */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Trust & Explainability</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Decision Replay</h3>
                  <p className="text-sm text-gray-600">
                    View detailed decision lineage and policy evaluations for any simulation.
                    Select a simulation from the Simulation History table above to see its decision replay.
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Decision Timeline</h3>
                  <p className="text-sm text-gray-600">
                    Track the lifecycle of decisions from creation to execution.
                    Available when viewing individual simulations.
                  </p>
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">Phase 24 Features</h3>
                <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                  <li>Confidence Stability Indicator: Shows confidence trend over time</li>
                  <li>What Changed Panel: Compare current vs previous analysis</li>
                  <li>Natural Language Summaries: Human-readable explanations</li>
                  <li>Tooltips: Hover over metrics for detailed explanations</li>
                  <li>Strategy Reliability Badges: Visual indicators of strategy performance</li>
                </ul>
              </div>
            </div>

            {/* Phase C1-C5: Core Vision Features */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Core Execution Features</h2>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">⚙️ Execution Steps (C1)</h3>
                  <p className="text-sm text-gray-600">
                    Multi-step execution engine with compensation logic. View step-by-step progress, 
                    status, and failure handling in simulation details.
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">✓ Compliance Reasoning (C2)</h3>
                  <p className="text-sm text-gray-600">
                    Explainable compliance decisions with rule evaluations and document requirements. 
                    See detailed compliance analysis in simulation details.
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">🚪 Execution Gates (C5)</h3>
                  <p className="text-sm text-gray-600">
                    Pre-execution gating with KYC, AML, and Tax checks. All gates must pass before execution. 
                    View gate status in simulation details.
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">📦 Logistics Tracking (C4)</h3>
                  <p className="text-sm text-gray-600">
                    Physical shipment tracking with condition monitoring. View temperature, humidity, 
                    shock events, and condition scores in simulation details.
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">🔮 Counterfactual Analysis (C3)</h3>
                  <p className="text-sm text-gray-600">
                    What-if analysis comparing actual outcomes vs no-action baseline. See ROI delta, 
                    risk delta, and opportunity cost in simulation details.
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">📋 Decision Replay (C1-C5)</h3>
                  <p className="text-sm text-gray-600">
                    Complete decision lineage and timeline. View all execution steps, compliance, 
                    gates, logistics, and counterfactual in one place via "View Details" button.
                  </p>
                </div>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-green-900 mb-2">How to Use</h3>
                <ol className="text-sm text-green-800 space-y-1 list-decimal list-inside">
                  <li>Go to <strong>Simulation History</strong> table above</li>
                  <li>Click <strong>"View Details"</strong> on any simulation</li>
                  <li>Explore tabs: Execution Steps, Compliance, Gates, Logistics, Counterfactual, Decision Replay</li>
                  <li>For APPROVED simulations, click <strong>"Execute"</strong> to trigger execution steps</li>
                </ol>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
