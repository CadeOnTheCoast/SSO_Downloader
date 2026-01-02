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
    const [filters, setFilters] = useState<FilterState>({ limit: 2000 })
    const [page, setPage] = useState(1)
    const [sortBy, setSortBy] = useState<string>('volume_gallons')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
    const pageSize = 50

    useEffect(() => {
        const supabase = createClient()
        supabase.auth.getUser().then(({ data }) => {
            if (data.user) setUserEmail(data.user.email || 'User')
        })

        // Initialize with previous calendar year
        const now = new Date()
        const prevYear = now.getFullYear() - 1
        const startDate = `${prevYear}-01-01`
        const endDate = `${prevYear}-12-31`

        handleFilterChange({
            start_date: startDate,
            end_date: endDate,
            limit: 2000
        })
    }, [])

    const handleFilterChange = async (newFilters: FilterState) => {
        setLoading(true)
        setFilters(newFilters)
        setPage(1)

        try {
            const [sum, recs] = await Promise.all([
                fetchSummary(newFilters),
                fetchRecords(newFilters, 0, pageSize, sortBy, sortOrder)
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
            const recs = await fetchRecords(filters, offset, pageSize, sortBy, sortOrder)
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

    const handleSortChange = async (key: string, direction: 'asc' | 'desc') => {
        setSortBy(key)
        setSortOrder(direction)
        setLoading(true)
        setPage(1)
        try {
            const recs = await fetchRecords(filters, 0, pageSize, key, direction)
            setRecords(recs.records)
        } catch (error) {
            console.error("Sort error:", error)
        } finally {
            setLoading(false)
        }
    }

    const getFullCsvUrl = () => {
        const params = new URLSearchParams()
        Object.entries(filters).forEach(([key, value]) => {
            if (value === undefined || value === null) return
            if (Array.isArray(value)) {
                value.forEach(v => params.append(key, v))
            } else {
                params.append(key, value.toString())
            }
        })
        return `/api/ssos.csv?${params.toString()}`
    }

    const handleDownload = () => {
        window.location.href = getFullCsvUrl()
    }

    return (
        <div className="flex min-h-screen flex-col bg-white text-brand-charcoal">
            <header className="border-b border-brand-sage/10 bg-white/80 backdrop-blur px-8 py-5 sticky top-0 z-10 shadow-sm">
                <div className="mx-auto flex max-w-7xl items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-brand-teal flex items-center justify-center shadow-md">
                            <span className="font-heading font-bold text-white text-xl">M</span>
                        </div>
                        <h1 className="text-2xl font-heading font-bold text-brand-charcoal tracking-wider">
                            Mobile Baykeeper <span className="text-brand-teal">SSO Explorer V5</span>
                        </h1>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className="text-xs font-bold text-brand-charcoal/40 uppercase tracking-widest border-r border-brand-sage/10 pr-6">
                            {userEmail}
                        </span>
                    </div>
                </div>
            </header>

            <main className="mx-auto w-full max-w-7xl p-8 space-y-8">
                {/* Header Section */}
                <div className="flex justify-between items-center bg-brand-sage/5 p-8 rounded-lg border border-brand-sage/10">
                    <div>
                        <h2 className="text-4xl font-heading font-bold text-brand-charcoal">Dashboard</h2>
                        <p className="text-brand-charcoal/60 mt-2 font-medium">Real-time overview of sewage overflow events in Alabama.</p>
                    </div>
                    <button
                        onClick={handleDownload}
                        className="bg-brand-teal hover:bg-brand-charcoal text-white font-heading font-bold tracking-widest uppercase px-8 py-3 rounded-md shadow-lg transition-all transform hover:-translate-y-0.5 active:translate-y-0"
                    >
                        Export Data
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
                    onSortChange={handleSortChange}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                    hasNextPage={records.length === pageSize}
                    fullCsvUrl={getFullCsvUrl()}
                />
            </main>
        </div>
    )
}
