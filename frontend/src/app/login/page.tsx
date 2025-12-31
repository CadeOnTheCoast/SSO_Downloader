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
                    <div className="inline-flex h-12 w-12 rounded-full bg-brand-teal items-center justify-center shadow-md mb-4">
                        <span className="font-heading font-bold text-white text-2xl">M</span>
                    </div>
                    <h1 className="text-4xl font-heading font-bold text-brand-charcoal tracking-tight">
                        MOBILE BAYKEEPER <span className="text-brand-teal">SSO</span>
                    </h1>
                    <p className="mt-4 text-brand-charcoal/60 font-medium">
                        Sign in with your email to access the dashboard.
                    </p>
                </div>

                <form className="space-y-6">
                    <div>
                        <label
                            htmlFor="email"
                            className="block text-xs font-bold text-brand-charcoal/40 uppercase tracking-widest mb-2"
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
                            className="block w-full rounded-md border border-brand-sage/20 bg-brand-sage/5 px-4 py-3 text-brand-charcoal placeholder:text-brand-charcoal/20 shadow-sm transition-all focus:border-brand-teal focus:bg-white focus:outline-none focus:ring-4 focus:ring-brand-teal/10"
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
                        className="flex w-full items-center justify-center rounded-md bg-brand-teal px-4 py-3 text-sm font-heading font-bold tracking-widest uppercase text-white shadow-lg shadow-brand-teal/20 transition-all hover:bg-brand-charcoal hover:-translate-y-0.5 active:translate-y-0"
                    >
                        Send Magic Link
                    </button>
                </form>

                <p className="mt-8 text-center text-[10px] font-bold text-brand-charcoal/30 uppercase tracking-[0.2em]">
                    Restricted to @mobilebaykeeper.org and authorized domains.
                </p>
            </div>
        </div>
    )
}
