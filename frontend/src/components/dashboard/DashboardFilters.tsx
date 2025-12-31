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
    const [filters, setFilters] = useState<FilterState>(() => {
        const now = new Date()
        return {
            start_date: `${now.getFullYear()}-01-01`,
            end_date: now.toISOString().split('T')[0],
            limit: 1000
        }
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
        return <div className="text-brand-sage text-sm animate-pulse font-medium">Loading filters...</div>
    }

    if (!options) return null

    return (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg border border-brand-sage/20 shadow-sm space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                {/* Utility Searchable Selection */}
                <div className="space-y-2 lg:col-span-2">
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">Utility / Permittee</label>
                    <div className="relative group">
                        <Search className="absolute left-3 top-2.5 h-4 w-4 text-brand-sage/60 group-focus-within:text-brand-teal transition-colors" />
                        <input
                            list="utility-options"
                            className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg pl-10 pr-3 py-2 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all"
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
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">Permit ID (Optional)</label>
                    <input
                        type="text"
                        className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg px-3 py-2 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all uppercase placeholder:text-brand-sage/30"
                        placeholder="AL0000000"
                        value={filters.permit || ''}
                        onChange={(e) => handleChange('permit', e.target.value || undefined)}
                    />
                </div>

                {/* County Select */}
                <div className="space-y-2">
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">County</label>
                    <div className="relative">
                        <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-brand-sage/60" />
                        <select
                            className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg pl-10 pr-3 py-2 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all appearance-none cursor-pointer"
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
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">Start Date</label>
                    <div className="relative">
                        <Calendar className="absolute left-3 top-2.5 h-4 w-4 text-brand-teal z-10 pointer-events-none" />
                        <input
                            type="date"
                            className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg pl-10 pr-3 py-2 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all [color-scheme:light]"
                            value={filters.start_date || ''}
                            onChange={(e) => handleChange('start_date', e.target.value || undefined)}
                        />
                    </div>
                </div>

                {/* End Date */}
                <div className="space-y-2">
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">End Date</label>
                    <div className="relative">
                        <Calendar className="absolute left-3 top-2.5 h-4 w-4 text-brand-teal z-10 pointer-events-none" />
                        <input
                            type="date"
                            className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg pl-10 pr-3 py-2 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all [color-scheme:light]"
                            value={filters.end_date || ''}
                            onChange={(e) => handleChange('end_date', e.target.value || undefined)}
                        />
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">Row Limit</label>
                    <input
                        type="number"
                        min="1"
                        max="20000"
                        className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg px-3 py-2 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all"
                        value={filters.limit || ''}
                        onChange={(e) => handleChange('limit', e.target.value ? parseInt(e.target.value) : undefined)}
                    />
                </div>
            </div>

            <div className="flex justify-end pt-2">
                <button
                    type="submit"
                    disabled={isLoading}
                    className="bg-brand-sage hover:bg-brand-sage/90 text-white text-sm font-heading font-bold px-6 py-2.5 rounded-lg shadow-sm hover:shadow transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-widest"
                >
                    {isLoading && <Loader2 className="w-4 h-4 animate-spin text-white" />}
                    Apply Filters
                </button>
            </div>
        </form>
    )
}
