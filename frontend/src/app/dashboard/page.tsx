'use client'

import React, { useState, useEffect } from 'react'
import { SSOOverview } from '@/components/dashboard/SSOOverview'
import { SSOCharts } from '@/components/dashboard/SSOCharts'
import { SSOTable } from '@/components/dashboard/SSOTable'
import { DashboardFilters } from '@/components/dashboard/DashboardFilters'
import { useSearchParams } from 'next/navigation'
import { FilterState, DashboardSummary, SeriesPoint, BarGroup, SSORecord, fetchSummary, fetchSeriesByDate, fetchSeriesByUtility, fetchRecords } from '@/lib/api'
import { createClient } from '@/lib/supabase/client' // Use client-side supbase for auth check if needed, or rely on layout/middleware

export default function DashboardPage() {
    // Auth check (basic) - assuming middleware handles protection generally, 
    // but for username display we might need context. 
    // For now, I'll mock the user or fetch it client side if critically needed.
    const [userEmail, setUserEmail] = useState<string>('')
    const [loading, setLoading] = useState(false)

    // Data State
    const [summary, setSummary] = useState<DashboardSummary | null>(null)
    const [timeSeries, setTimeSeries] = useState<SeriesPoint[]>([])
    const [barGroups, setBarGroups] = useState<BarGroup[]>([])
    const [records, setRecords] = useState<SSORecord[]>([])
    const [totalRecords, setTotalRecords] = useState(0)

    // Filter State
    const [filters, setFilters] = useState<FilterState>({ limit: 1000 })
    const [page, setPage] = useState(1)
    const pageSize = 50

    useEffect(() => {
        // Quick auth check
        const supabase = createClient()
        supabase.auth.getUser().then(({ data }) => {
            if (data.user) setUserEmail(data.user.email || 'User')
            // else redirect('/login') // handled by middleware usually
        })

        // Initial load
        handleFilterChange({})
    }, [])

    const handleFilterChange = async (newFilters: FilterState) => {
        setLoading(true)
        setFilters(newFilters)
        setPage(1) // Reset page on filter change

        try {
            const [sum, time, bar, recs] = await Promise.all([
                fetchSummary(newFilters),
                fetchSeriesByDate(newFilters),
                fetchSeriesByUtility(newFilters),
                fetchRecords(newFilters, 0, pageSize)
            ])

            setSummary(sum)
            setTimeSeries(time.points)
            setBarGroups(bar.bars)
            setRecords(recs.records)
            setTotalRecords(recs.total)
        } catch (error) {
            console.error("Dashboard error:", error)
        } finally {
            setLoading(false)
        }
    }

    const handlePageChange = async (newPage: number) => {
        setLoading(true)
        setPage(newPage)
        const offset = (newPage - 1) * pageSize
        try {
            const recs = await fetchRecords(filters, offset, pageSize)
            setRecords(recs.records)
        } catch (error) {
            console.error("Pagination error:", error)
        } finally {
            setLoading(false)
        }
    }

    const handlePieClick = (utilityName: string) => {
        // "click a slice and the table updates to just show spills from that utility"
        // We update the utility_name filter (we might need to map name to ID if API requires ID, 
        // but API supports utility_name query param).
        // Since my filter component primarily uses ID, I might need to support name or just fill the form?
        // For now, I'll trigger a filter update with utility_name.
        // NOTE: The current DashboardFilters component uses ID. I should probably support Name or find ID.
        // API supports `utility_name`.
        const updatedFilters = { ...filters, utility_name: utilityName }
        handleFilterChange(updatedFilters)
    }

    const handleDownload = () => {
        const params = new URLSearchParams(filters as any)
        window.location.href = `/download?${params.toString()}`
    }

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
                            {userEmail}
                        </span>
                    </div>
                </div>
            </header>

            <main className="mx-auto w-full max-w-7xl p-8 space-y-8">
                {/* Header Section */}
                <div className="flex justify-between items-end">
                    <div>
                        <h2 className="text-3xl font-bold text-white">Dashboard</h2>
                        <p className="text-slate-400 mt-1">Real-time overview of sewage overflow events.</p>
                    </div>
                    <button
                        onClick={handleDownload}
                        className="bg-slate-800 hover:bg-slate-700 text-white text-sm px-4 py-2 rounded border border-slate-700 transition-colors"
                    >
                        Download CSV
                    </button>
                </div>

                {/* Filters */}
                <DashboardFilters onFilterChange={handleFilterChange} isLoading={loading} />

                {/* Stats Overview */}
                <SSOOverview summary={summary} />

                {/* Main Charts */}
                <SSOCharts
                    timeSeries={timeSeries}
                    barGroups={barGroups}
                    onPieClick={handlePieClick}
                />

                {/* Recent Reports Table */}
                <SSOTable
                    records={records}
                    page={page}
                    onChangePage={handlePageChange}
                    hasNextPage={records.length === pageSize} // Simple check, could use total count
                />
            </main>
        </div>
    )
}

