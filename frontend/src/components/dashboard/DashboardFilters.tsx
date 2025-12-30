'use client'

import { useState, useEffect } from 'react'
import { FilterOptions, FilterState, fetchFilters } from '@/lib/api'
import { Loader2, Search, Calendar, MapPin, ListFilter } from 'lucide-react'

interface DashboardFiltersProps {
    onFilterChange: (filters: FilterState) => void
    isLoading: boolean
}

export function DashboardFilters({ onFilterChange, isLoading }: DashboardFiltersProps) {
    const [options, setOptions] = useState<FilterOptions | null>(null)
    const [filters, setFilters] = useState<FilterState>({
        limit: 1000 // Default limit
    })
    const [loadingOptions, setLoadingOptions] = useState(true)

    useEffect(() => {
        fetchFilters()
            .then(setOptions)
            .finally(() => setLoadingOptions(false))
    }, [])

    const handleChange = (key: keyof FilterState, value: any) => {
        setFilters(prev => ({ ...prev, [key]: value }))
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        onFilterChange(filters)
    }

    if (loadingOptions) {
        return <div className="text-slate-400 text-sm">Loading filters...</div>
    }

    if (!options) return null

    return (
        <form onSubmit={handleSubmit} className="bg-slate-900/50 p-4 rounded-lg border border-slate-800 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                {/* Utility Searchable Selection */}
                <div className="space-y-2 lg:col-span-2">
                    <label className="text-xs text-slate-400 font-medium">Utility / Permittee</label>
                    <div className="relative group">
                        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                        <input
                            list="utility-options"
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all"
                            placeholder="Search permittee..."
                            value={filters.utility_id || ''}
                            onChange={(e) => handleChange('utility_id', e.target.value.split(' - ')[0] || undefined)}
                        />
                        <datalist id="utility-options">
                            {options.utilities.map(u => (
                                <option key={u.id} value={`${u.id} - ${u.name}`} />
                            ))}
                        </datalist>
                    </div>
                </div>

                {/* Optional Permit ID Input */}
                <div className="space-y-2">
                    <label className="text-xs text-slate-400 font-medium">Permit ID (Optional)</label>
                    <input
                        type="text"
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all uppercase placeholder:text-slate-600"
                        placeholder="AL0000000"
                        value={filters.permit || ''}
                        onChange={(e) => handleChange('permit', e.target.value || undefined)}
                    />
                </div>

                {/* County Select */}
                <div className="space-y-2">
                    <label className="text-xs text-slate-400 font-medium tracking-wider uppercase opacity-60">County</label>
                    <div className="relative">
                        <MapPin className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
                        <select
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all appearance-none cursor-pointer"
                            value={filters.county || ''}
                            onChange={(e) => handleChange('county', e.target.value || undefined)}
                        >
                            <option value="">All Counties</option>
                            {options.counties.map(c => (
                                <option key={c} value={c}>
                                    {c}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Start Date */}
                <div className="space-y-2">
                    <label className="text-xs text-slate-400 font-medium">Start Date</label>
                    <input
                        type="date"
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        value={filters.start_date || ''}
                        onChange={(e) => handleChange('start_date', e.target.value || undefined)}
                    />
                </div>

                {/* End Date */}
                <div className="space-y-2">
                    <label className="text-xs text-slate-400 font-medium">End Date</label>
                    <input
                        type="date"
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        value={filters.end_date || ''}
                        onChange={(e) => handleChange('end_date', e.target.value || undefined)}
                    />
                </div>

                {/* Limit */}
                <div className="space-y-2">
                    <label className="text-xs text-slate-400 font-medium">Row Limit</label>
                    <input
                        type="number"
                        min="1"
                        max="20000"
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        value={filters.limit || ''}
                        onChange={(e) => handleChange('limit', e.target.value ? parseInt(e.target.value) : undefined)}
                    />
                </div>
            </div>

            <div className="flex justify-end pt-2">
                <button
                    type="submit"
                    disabled={isLoading}
                    className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                    Apply Filters
                </button>
            </div>
        </form>
    )
}
