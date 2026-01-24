import Link from 'next/link'
import { SignedIn, SignedOut, SignInButton, SignOutButton, useUser } from '@clerk/nextjs'

export default function NavBar(){
  const { user } = useUser()
  return (
    <header className="bg-white shadow-md">
      <div className="max-w-6xl mx-auto p-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/" className="text-wine-700 font-bold text-xl hover:text-wine-500">Wine Invest</Link>
          <nav className="hidden md:flex space-x-3">
            <Link href="/dashboard" className="text-gray-600 hover:text-wine-700 px-2 py-1">Dashboard</Link>
            <Link href="#" className="text-gray-600 hover:text-wine-700 px-2 py-1">Market</Link>
            <Link href="#" className="text-gray-600 hover:text-wine-700 px-2 py-1">Portfolio</Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <SignedOut>
            <SignInButton mode="modal">
              <button className="px-4 py-2 bg-wine-500 text-white rounded hover:bg-wine-700 transition-colors">
                Sign In
              </button>
            </SignInButton>
            <Link href="/register" className="px-4 py-2 border border-wine-700 text-wine-700 rounded hover:bg-wine-50 transition-colors">
              Register
            </Link>
          </SignedOut>

          <SignedIn>
            <div className="flex items-center gap-3">
              <div className="text-sm text-gray-600 hidden sm:block">
                {user ? (user.firstName || user.emailAddresses?.[0]?.emailAddress || 'User') : ''}
              </div>
              <SignOutButton>
                <button className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors font-medium">
                  Sign Out
                </button>
              </SignOutButton>
            </div>
          </SignedIn>
        </div>
      </div>
    </header>
  )
}

