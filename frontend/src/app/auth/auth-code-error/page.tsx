'use client'

import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function AuthCodeError() {
    const router = useRouter()

    useEffect(() => {
        // Auto-redirect to login after showing error
        const timer = setTimeout(() => {
            router.push('/login')
        }, 5000)
        return () => clearTimeout(timer)
    }, [router])

    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 text-white p-8">
            <div className="max-w-md w-full space-y-6 text-center">
                <div className="h-12 w-12 rounded-full bg-red-600 flex items-center justify-center mx-auto">
                    <span className="text-2xl">✕</span>
                </div>

                <h1 className="text-2xl font-bold">Authentication Error</h1>

                <div className="space-y-4 text-slate-400">
                    <p>
                        There was a problem with your magic link. This could happen if:
                    </p>
                    <ul className="list-disc list-inside space-y-2 text-left">
                        <li>The link has expired (magic links are valid for a limited time)</li>
                        <li>The link has already been used</li>
                        <li>There was a network issue during authentication</li>
                    </ul>
                    <p className="text-sm">
                        Redirecting to login page in 5 seconds...
                    </p>
                </div>

                <button
                    onClick={() => router.push('/login')}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded transition-colors"
                >
                    Return to Login
                </button>
            </div>
        </div>
    )
}
