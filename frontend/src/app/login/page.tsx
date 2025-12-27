import { login } from './actions'

export default function LoginPage({
    searchParams,
}: {
    searchParams: { error?: string; success?: string }
}) {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6">
            <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl ring-1 ring-slate-200">
                <div className="mb-8 text-center">
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
                        SSO Downloader
                    </h1>
                    <p className="mt-2 text-slate-600">
                        Sign in with your email to access the dashboard.
                    </p>
                </div>

                <form className="space-y-6">
                    <div>
                        <label
                            htmlFor="email"
                            className="block text-sm font-semibold text-slate-700"
                        >
                            Email address
                        </label>
                        <input
                            id="email"
                            name="email"
                            type="email"
                            autoComplete="email"
                            required
                            placeholder="you@mobilebaykeeper.org"
                            className="mt-1 block w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-900 shadow-sm transition-focus focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10"
                        />
                    </div>

                    {searchParams.error && (
                        <div className="rounded-lg bg-red-50 p-4 text-sm font-medium text-red-800 ring-1 ring-red-200">
                            {searchParams.error}
                        </div>
                    )}

                    {searchParams.success && (
                        <div className="rounded-lg bg-emerald-50 p-4 text-sm font-medium text-emerald-800 ring-1 ring-emerald-200">
                            {searchParams.success}
                        </div>
                    )}

                    <button
                        formAction={login}
                        className="flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-blue-500/25 transition-all hover:bg-blue-700 active:scale-[0.98]"
                    >
                        Send Magic Link
                    </button>
                </form>

                <p className="mt-8 text-center text-xs text-slate-500">
                    Restricted to @mobilebaykeeper.org and authorized domains.
                </p>
            </div>
        </div>
    )
}
