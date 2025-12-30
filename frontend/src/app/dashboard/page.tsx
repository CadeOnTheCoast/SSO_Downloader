'use client'

import React, { useState, useEffect } from 'react'
import { SSOOverview } from '@/components/dashboard/SSOOverview'
import { SSOCharts } from '@/components/dashboard/SSOCharts'
import { SSOTable } from '@/components/dashboard/SSOTable'
import { DashboardFilters } from '@/components/dashboard/DashboardFilters'
import { createClient } from '@/lib/supabase/client'
import {
    FilterState,
    DashboardSummary,
    SeriesPoint,
    BarGroup,
    SSORecord,
    fetchSummary,
    fetchRecords
} from '@/lib/api'

export default function DashboardPage() {
    const [userEmail, setUserEmail] = useState<string>('')
    const [loading, setLoading] = useState(false)

    // Data State
    const [summary, setSummary] = useState<DashboardSummary | null>(null)
    const [timeSeries, setTimeSeries] = useState<SeriesPoint[]>([])
    const [barGroups, setBarGroups] = useState<BarGroup[]>([])
    const [records, setRecords] = useState<SSORecord[]>([])
    const [totalRecords, setTotalRecords] = useState(0)
    const [receivingWaters, setReceivingWaters] = useState<{ name: string, total_volume: number, spills: number }[]>([])

    // Filter State
    const [filters, setFilters] = useState<FilterState>({ limit: 1000 })
    const [page, setPage] = useState(1)
    const pageSize = 50

    useEffect(() => {
        const supabase = createClient()
        supabase.auth.getUser().then(({ data }) => {
            if (data.user) setUserEmail(data.user.email || 'User')
        })
        handleFilterChange({})
    }, [])

    const handleFilterChange = async (newFilters: FilterState) => {
        setLoading(true)
        setFilters(newFilters)
        setPage(1)

        try {
            const [sum, recs] = await Promise.all([
                fetchSummary(newFilters),
                fetchRecords(newFilters, 0, pageSize)
            ])

            setSummary(sum)

            // Module H/I Refactor: Use data directly from the summary payload where available
            if (sum.time_series) {
                setTimeSeries(sum.time_series)
            }

            if (sum.by_utility) {
                const bars: BarGroup[] = sum.by_utility.map((u: { utility_name: string; spill_count: number; total_volume: number }) => ({
                    label: u.utility_name,
                    count: u.spill_count,
                    total_volume_gallons: u.total_volume
                }))
                setBarGroups(bars)
            }

            if (sum.by_receiving_water) {
                setReceivingWaters(sum.by_receiving_water)
            }

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
        const updatedFilters = { ...filters, utility_name: utilityName }
        handleFilterChange(updatedFilters)
    }

    const getFullCsvUrl = () => {
        const params = new URLSearchParams()
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined) params.append(key, value.toString())
        })
        return `/api/ssos.csv?${params.toString()}`
    }

    const handleDownload = () => {
        window.location.href = getFullCsvUrl()
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
                    receivingWaters={receivingWaters}
                    onPieClick={handlePieClick}
                />

                {/* Recent Reports Table */}
                <SSOTable
                    records={records}
                    page={page}
                    onChangePage={handlePageChange}
                    hasNextPage={records.length === pageSize}
                    fullCsvUrl={getFullCsvUrl()}
                />
            </main>
        </div>
    )
}
