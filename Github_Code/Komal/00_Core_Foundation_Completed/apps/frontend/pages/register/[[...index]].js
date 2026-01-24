import { useState, useEffect } from 'react';
import { SignUp } from '@clerk/nextjs';
import Head from 'next/head';
import Link from 'next/link';
import Image from 'next/image';

export default function RegisterPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <>
      <Head>
        <title>Create Account | Carbon Trade</title>
        <meta name="description" content="Create your Carbon Trade account" />
      </Head>
      
      <div className="min-h-screen gradient-bg relative overflow-hidden">
        {/* Centered Background Image with Fade Effects - Moved Left */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden z-0">
          <div 
            className="absolute left-[25%] top-[55%] -translate-x-1/2 -translate-y-1/2 animate-float"
            style={{ 
              '--rotate-start': '0deg',
              animationDelay: '0s',
              animationDuration: '12s'
            }}
          >
            <div className="relative">
              {/* Left fade overlay - smooth side fade */}
              <div className="absolute left-0 top-0 bottom-0 w-80 bg-gradient-to-r from-[#020617] via-[#020617]/50 to-transparent z-10 pointer-events-none"></div>
              {/* Right fade overlay - smooth side fade */}
              <div className="absolute right-0 top-0 bottom-0 w-80 bg-gradient-to-l from-[#020617] via-[#020617]/50 to-transparent z-10 pointer-events-none"></div>
              {/* Image with lower opacity */}
              <Image
                src="/car-1-removebg-preview.png"
                alt="Green economy illustration"
                width={950}
                height={950}
                className="drop-shadow-[0_50px_120px_rgba(128,0,32,0.15)] opacity-45 hover:opacity-55 transition-all duration-700"
                style={{ filter: 'brightness(1.1) contrast(1.05)' }}
                priority
              />
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
          <div className="w-full max-w-6xl grid md:grid-cols-2 gap-8 items-stretch md:gap-12 lg:gap-16 md:min-h-[80vh]">
            
            {/* Left Side - Branding & Welcome */}
            <div className={`hidden md:flex md:flex-col md:h-full md:py-8 ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
              <div className="space-y-4">
                <div className="inline-block">
                  <h1 className="text-5xl font-cinzel font-bold text-white text-shadow mb-3">
                    Carbon Trade
                  </h1>
                  <div className="h-1 w-20 bg-gradient-to-r from-gold to-transparent"></div>
                </div>
                
                <div className="space-y-4">
                  <p className="text-xl text-text-light font-lato font-light leading-relaxed text-shadow">
                    Sustainable Assets.
                    <br />
                    <span className="text-gold font-medium">Future Value.</span>
                  </p>
                  
                  <p className="text-base text-text-muted font-lato leading-relaxed max-w-lg">
                    A simple platform to trade verified carbon credits globally.
                  </p>
                  
                  <p className="text-sm text-text-muted font-lato leading-relaxed max-w-lg">
                    Help companies meet climate goals while creating real financial value.
                  </p>
                </div>
              </div>

              {/* Feature highlights */}
              <div className="space-y-4 mt-36">
                <div className={`flex items-start gap-3 ${mounted ? 'animate-slide-in-right' : 'opacity-0'}`} style={{ animationDelay: '0.2s' }}>
                  <div className="w-10 h-10 glass-effect rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-white font-lato font-semibold text-sm">Verified Credits</h3>
                    <p className="text-text-muted text-xs leading-relaxed">Every credit audited & compliant</p>
                  </div>
                </div>

                <div className={`flex items-start gap-3 ${mounted ? 'animate-slide-in-right' : 'opacity-0'}`} style={{ animationDelay: '0.3s' }}>
                  <div className="w-10 h-10 glass-effect rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-white font-lato font-semibold text-sm">Live Market Prices</h3>
                    <p className="text-text-muted text-xs leading-relaxed">Real-time carbon price tracking</p>
                  </div>
                </div>

                <div className={`flex items-start gap-3 ${mounted ? 'animate-slide-in-right' : 'opacity-0'}`} style={{ animationDelay: '0.4s' }}>
                  <div className="w-10 h-10 glass-effect rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-white font-lato font-semibold text-sm">Secure & Compliant</h3>
                    <p className="text-text-muted text-xs leading-relaxed">Built-in global regulations</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Side - Registration Form */}
            <div className={`w-full md:ml-8 lg:ml-16 max-w-sm md:max-w-md ${mounted ? 'animate-scale-in' : 'opacity-0'}`}>
              <div className="glass-card rounded-2xl p-5 md:p-7 shadow-2xl relative overflow-hidden">
                {/* subtle top highlight */}
                <div className="pointer-events-none absolute -top-32 left-1/2 -translate-x-1/2 w-80 h-80 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.08),transparent_60%)]" />
                {/* Mobile Branding */}
                <div className="md:hidden text-center mb-4 animate-fade-in-up">
                  <h1 className="text-3xl font-cinzel font-bold text-white text-shadow mb-1">
                    Carbon Trade
                  </h1>
                  <p className="text-text-muted text-xs animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
                    Create your account to start trading and managing your portfolio
                  </p>
                </div>

                {/* Desktop Header */}
                <div className="hidden md:block mb-5">
                  <h2 className="text-2xl font-cinzel font-bold text-white text-shadow mb-1 animate-fade-in-up">
                    Create Your Account
                  </h2>
                  <p className="text-text-muted font-lato text-sm animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
                    Welcome! Join us and start trading wines globally. Fill in your details to get started.
                  </p>
                </div>

                {/* Clerk Sign Up Component */}
                <div className="clerk-sign-up-wrapper">
                  <SignUp 
                    path="/register" 
                    routing="path" 
                    signInUrl="/sign-in"
                    appearance={{
                      elements: {
                        rootBox: "mx-auto",
                        card: "bg-transparent shadow-none border-none",
                        headerTitle: "hidden",
                        headerSubtitle: "hidden",
                        socialButtonsBlockButton: "glass-effect hover:bg-white/10 transition-all duration-300 text-white border-border-subtle font-lato rounded-lg",
                        socialButtonsBlockButtonText: "text-white font-lato font-medium",
                        formButtonPrimary: "bg-burgundy hover:bg-dark-garnet text-white font-cinzel font-semibold transition-all duration-300 shadow-lg hover:shadow-xl rounded-lg py-3 px-6 text-base",
                        formFieldInput: "bg-input-dark border-border-subtle text-text-light font-lato focus:border-gold focus:ring-gold rounded-lg transition-all duration-300",
                        formFieldLabel: "text-text-light font-lato font-medium mb-2",
                        footerActionLink: "text-gold hover:text-gold/80 font-lato font-medium transition-all duration-200",
                        identityPreviewText: "text-text-light font-lato",
                        identityPreviewEditButton: "text-gold hover:text-gold/80 transition-all duration-200",
                        formResendCodeLink: "text-gold hover:text-gold/80 font-lato font-medium transition-all duration-200",
                        otpCodeFieldInput: "bg-input-dark border-border-subtle text-text-light focus:border-gold rounded-lg transition-all duration-300",
                        alertText: "text-text-light font-lato rounded-lg",
                        formFieldErrorText: "text-red-400 font-lato text-sm animate-fade-in-scale",
                        formFieldSuccessText: "text-green-400 font-lato text-sm animate-fade-in-scale",
                        formFieldInputShowPasswordButton: "text-gold hover:text-gold/80 transition-all duration-200",
                        formFieldInputShowPasswordIcon: "text-gold",
                      },
                      variables: {
                        colorPrimary: '#800020',
                        colorText: '#e0e0e0',
                        colorTextSecondary: '#a0a0a0',
                        colorBackground: 'transparent',
                        colorInputBackground: '#3a2d35',
                        colorInputText: '#e0e0e0',
                        borderRadius: '0.5rem',
                      }
                    }}
                  />
                </div>

                {/* Additional Links */}
                <div className="mt-4 text-center space-y-1.5 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
                  <p className="text-text-muted text-xs font-lato">
                    Already have an account?{' '}
                    <Link 
                      href="/sign-in" 
                      className="text-gold hover:text-gold/80 font-semibold transition-all duration-200 hover:underline inline-flex items-center gap-1 group"
                    >
                      Sign in
                      <svg className="w-3 h-3 transition-transform duration-200 group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </Link>
                  </p>
                  <Link 
                    href="/" 
                    className="inline-flex items-center gap-1 text-text-muted hover:text-text-light text-xs font-lato transition-all duration-200 group"
                  >
                    <svg className="w-3 h-3 transition-transform duration-200 group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Back to home
                  </Link>
                </div>
              </div>

              {/* Trust Badges */}
              <div className="mt-4 flex flex-wrap justify-center gap-4 text-text-muted text-xs font-lato">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-gold" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>Secure</span>
                </div>
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-gold" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                    <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                  </svg>
                  <span>Verified</span>
                </div>
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-gold" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>Trusted</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Decorative Elements */}
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-gold/50 to-transparent"></div>
      </div>

      <style jsx global>{`
        .clerk-sign-up-wrapper {
          animation: fadeIn 0.6s ease-out;
        }
        
        .clerk-sign-up-wrapper * {
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* Custom scrollbar for Clerk components */
        .clerk-sign-up-wrapper ::-webkit-scrollbar {
          width: 8px;
        }

        .clerk-sign-up-wrapper ::-webkit-scrollbar-track {
          background: rgba(58, 45, 53, 0.5);
          border-radius: 4px;
        }

        .clerk-sign-up-wrapper ::-webkit-scrollbar-thumb {
          background: rgba(212, 175, 55, 0.5);
          border-radius: 4px;
          transition: background 0.3s ease;
        }

        .clerk-sign-up-wrapper ::-webkit-scrollbar-thumb:hover {
          background: rgba(212, 175, 55, 0.7);
        }

        /* Enhanced form field animations */
        .clerk-sign-up-wrapper .cl-formField {
          animation: fade-in-up 0.4s ease-out forwards;
        }

        .clerk-sign-up-wrapper .cl-formField:nth-child(1) {
          animation-delay: 0.1s;
        }

        .clerk-sign-up-wrapper .cl-formField:nth-child(2) {
          animation-delay: 0.2s;
        }

        .clerk-sign-up-wrapper .cl-formField:nth-child(3) {
          animation-delay: 0.3s;
        }

        .clerk-sign-up-wrapper .cl-formField:nth-child(4) {
          animation-delay: 0.4s;
        }

        .clerk-sign-up-wrapper .cl-formField:nth-child(5) {
          animation-delay: 0.5s;
        }

        /* Smooth focus transitions */
        .clerk-sign-up-wrapper input:focus {
          outline: none;
        }

        /* Enhanced button hover effects */
        .clerk-sign-up-wrapper button:hover {
          transform: translateY(-1px);
        }

        .clerk-sign-up-wrapper button:active {
          transform: translateY(0);
        }
      `}</style>
    </>
  );
}

