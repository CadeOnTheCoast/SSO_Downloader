import Link from 'next/link'

export default function UnauthorizedPage() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6 text-center">
            <div className="max-w-md">
                <h1 className="text-6xl font-black text-slate-900">403</h1>
                <h2 className="mt-4 text-2xl font-bold text-slate-800">Access Denied</h2>
                <p className="mt-4 text-slate-600">
                    Your email domain is not authorized to access this platform. Please sign in with an official @mobilebaykeeper.org account.
                </p>
                <div className="mt-8">
                    <Link
                        href="/login"
                        className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-6 py-3 text-sm font-bold text-white shadow-xl transition-all hover:bg-slate-800"
                    >
                        Back to Login
                    </Link>
                </div>
            </div>
        </div>
    )
}
