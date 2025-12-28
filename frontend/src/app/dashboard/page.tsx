import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import { SSOOverview } from '@/components/dashboard/SSOOverview'
import { SSOCharts } from '@/components/dashboard/SSOCharts'
import { SSOTable } from '@/components/dashboard/SSOTable'
import _ from 'lodash'

export const revalidate = 0 // Disable caching for real-time data

export default async function DashboardPage() {
    const supabase = await createClient()

    // TEMP: Auth disabled for debugging
    // const {
    //     data: { user },
    // } = await supabase.auth.getUser()

    // if (!user) {
    //     return redirect('/login')
    // }

    const user = { email: 'debug@mobilebaykeeper.org' } // Mock user for display

    // Fetch all reports (optimized for dashboard)
    // efficient query for stats
    const { data: reports, error } = await supabase
        .from('sso_reports')
        .select('*')
        .order('date_sso_began', { ascending: false })

    if (error) {
        console.error("Error fetching reports:", error)
        return (
            <div className="p-8 text-center text-red-500">
                Error loading data. Please try again later.
            </div>
        )
    }

    // Process Data
    const totalSsos = reports.length
    const totalVolume = _.sumBy(reports, (r) => Number(r.volume_gallons) || 0)
    const uniqueUtilities = _.uniqBy(reports, 'utility_name').length

    // Top County
    const countyCounts = _.countBy(reports, 'county')
    const topCountyEntry = _.maxBy(_.entries(countyCounts), ([_, count]) => count)
    const topCounty = topCountyEntry ? `${topCountyEntry[0]} (${topCountyEntry[1]})` : "N/A"

    // Time Series (Monthly)
    const monthlyGroups = _.groupBy(reports, (r) => {
        if (!r.date_sso_began) return 'Unknown'
        return new Date(r.date_sso_began).toLocaleString('default', { month: 'short', year: '2-digit' })
    })

    // transform to array and reverse to show chronological order if needed, but 'reports' is desc
    // We want chronological for the chart
    const timeSeries = Object.entries(monthlyGroups)
        .map(([name, group]) => ({
            name,
            total: group.length
        }))
        // simplistic sort by date string might fail, ideally specific date sorting
        // fallback: rely on the assumption that if we iterate keys they might not be sorted.
        // Better:
        .sort((a, b) => {
            // simplified robust sort
            if (a.name === 'Unknown') return -1;
            return new Date('1 ' + a.name).getTime() - new Date('1 ' + b.name).getTime();
        })


    // County Data (Top 10)
    const countyData = Object.entries(countyCounts)
        .map(([name, total]) => ({ name: name || "Unknown", total }))
        .sort((a, b) => b.total - a.total)
        .slice(0, 10)

    return (
        <div className="flex min-h-screen flex-col bg-slate-950 text-white">
            <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur px-8 py-4 sticky top-0 z-10">
                <div className="mx-auto flex max-w-7xl items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center">
                            <span className="font-bold text-white">S</span>
                        </div>
                        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                            SSO Downloader
                        </h1>
                    </div>

                    <div className="flex items-center gap-4">
                        <span className="text-sm text-slate-400 border-r border-slate-700 pr-4">
                            {user.email}
                        </span>
                        <form action="/auth/signout" method="post">
                            <button className="text-sm font-semibold text-slate-300 hover:text-white transition-colors">
                                Sign out
                            </button>
                        </form>
                    </div>
                </div>
            </header>

            <main className="mx-auto w-full max-w-7xl p-8 space-y-8">
                {/* Header Section */}
                <div>
                    <h2 className="text-3xl font-bold text-white">Dashboard</h2>
                    <p className="text-slate-400 mt-1">Real-time overview of sewage overflow events in Alabama.</p>
                </div>

                {/* Stats Overview */}
                <SSOOverview
                    totalSsos={totalSsos}
                    totalVolume={totalVolume}
                    uniqueUtilities={uniqueUtilities}
                    topCounty={topCounty}
                />

                {/* Main Charts */}
                <SSOCharts
                    timeSeries={timeSeries}
                    countyData={countyData}
                />

                {/* Recent Reports Table */}
                <SSOTable reports={reports.slice(0, 50)} />
            </main>
        </div>
    )
}
