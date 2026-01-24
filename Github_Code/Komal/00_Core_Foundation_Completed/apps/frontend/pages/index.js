import Head from 'next/head'
import { useRouter } from 'next/router'
import { useEffect } from 'react'
import NavBar from '../components/NavBar'

export default function Home() {
  const router = useRouter()
  
  useEffect(() => {
    // Redirect to dashboard
    router.push('/dashboard')
  }, [router])
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-wine-50 to-white">
      <Head>
        <title>Wine Invest — Welcome</title>
      </Head>
      <NavBar />
      <main className="max-w-4xl mx-auto p-6">
        <section className="mt-12 bg-white p-8 rounded shadow">
          <h2 className="text-xl font-semibold">Redirecting to dashboard...</h2>
          <p className="mt-2 text-gray-600">Please wait...</p>
        </section>
      </main>
    </div>
  )
}

