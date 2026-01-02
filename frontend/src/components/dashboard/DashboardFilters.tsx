'use client'

import { useState, useEffect, useRef } from 'react'
import { FilterOptions, FilterState, fetchFilters } from '@/lib/api'
import { Loader2, Search, Calendar, MapPin, ListFilter, X, ChevronDown } from 'lucide-react'

interface DashboardFiltersProps {
    onFilterChange: (filters: FilterState) => void
    isLoading: boolean
}

export function DashboardFilters({ onFilterChange, isLoading }: DashboardFiltersProps) {
    const [options, setOptions] = useState<FilterOptions | null>(null)
    const [filters, setFilters] = useState<FilterState>(() => {
        const now = new Date()
        const prevYear = now.getFullYear() - 1
        return {
            start_date: `${prevYear}-01-01`,
            end_date: `${prevYear}-12-31`,
            limit: 2000
        }
    })
    const [loadingOptions, setLoadingOptions] = useState(true)
    const [utilitySearch, setUtilitySearch] = useState('')
    const [countySearch, setCountySearch] = useState('')
    const [showUtilityDropdown, setShowUtilityDropdown] = useState(false)
    const [showCountyDropdown, setShowCountyDropdown] = useState(false)
    const utilityRef = useRef<HTMLDivElement>(null)
    const countyRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        fetchFilters()
            .then(setOptions)
            .finally(() => setLoadingOptions(false))
    }, [])

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (utilityRef.current && !utilityRef.current.contains(event.target as Node)) {
                setShowUtilityDropdown(false)
            }
            if (countyRef.current && !countyRef.current.contains(event.target as Node)) {
                setShowCountyDropdown(false)
            }
        }
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                setShowUtilityDropdown(false)
                setShowCountyDropdown(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        document.addEventListener('keydown', handleKeyDown)
        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
            document.removeEventListener('keydown', handleKeyDown)
        }
    }, [])

    const handleChange = (key: keyof FilterState, value: any) => {
        setFilters(prev => ({ ...prev, [key]: value }))
    }

    const handleReset = () => {
        const now = new Date()
        const prevYear = now.getFullYear() - 1
        const resetFilters: FilterState = {
            start_date: `${prevYear}-01-01`,
            end_date: `${prevYear}-12-31`,
            limit: 2000
        }
        setFilters(resetFilters)
        setUtilitySearch('')
        setCountySearch('')
        onFilterChange(resetFilters)
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        onFilterChange(filters)
    }

    const filteredUtilities = options?.utilities.filter(u =>
        u.name.toLowerCase().includes(utilitySearch.toLowerCase()) ||
        u.id.toLowerCase().includes(utilitySearch.toLowerCase())
    ).slice(0, 50) || []

    const filteredCounties = options?.counties.filter(c =>
        c.toLowerCase().includes(countySearch.toLowerCase())
    ) || []

    const selectedUtilityName = options?.utilities.find(u => u.id === filters.utility_id)?.name || ''

    if (loadingOptions) {
        return <div className="text-brand-sage text-sm animate-pulse font-medium">Loading filters...</div>
    }

    if (!options) return null

    return (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg border border-brand-sage/20 shadow-sm space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                {/* Utility Searchable Selection */}
                <div className="space-y-2 lg:col-span-2" ref={utilityRef}>
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">Utility / Permittee</label>
                    <div className="relative group">
                        <Search className="absolute left-3 top-2.5 h-4 w-4 text-brand-sage/60 group-focus-within:text-brand-teal transition-colors" />
                        <input
                            type="text"
                            className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg pl-10 pr-10 py-2.5 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all"
                            placeholder={filters.utility_id ? selectedUtilityName : "Search permittee or permit id..."}
                            value={utilitySearch}
                            onFocus={() => setShowUtilityDropdown(true)}
                            onChange={(e) => {
                                setUtilitySearch(e.target.value)
                                setShowUtilityDropdown(true)
                            }}
                        />
                        {filters.utility_id && (
                            <button
                                type="button"
                                onClick={() => {
                                    handleChange('utility_id', undefined)
                                    setUtilitySearch('')
                                }}
                                className="absolute right-3 top-2.5 text-brand-sage hover:text-brand-teal transition-colors"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        )}
                        {showUtilityDropdown && (
                            <div className="absolute z-50 mt-1 w-full max-h-64 overflow-y-auto bg-white border border-brand-sage/20 rounded-lg shadow-xl py-1">
                                {filteredUtilities.length > 0 ? (
                                    filteredUtilities.map(u => (
                                        <button
                                            key={u.id}
                                            type="button"
                                            onClick={() => {
                                                setFilters(prev => ({ ...prev, utility_id: u.id, permit: undefined }))
                                                setUtilitySearch('')
                                                setShowUtilityDropdown(false)
                                            }}
                                            className="w-full text-left px-4 py-3 text-sm hover:bg-brand-sage/5 transition-colors border-b border-brand-sage/5 last:border-0"
                                        >
                                            <div className="font-bold text-brand-charcoal">{u.name}</div>
                                            <div className="text-xs text-brand-sage">{u.id}</div>
                                        </button>
                                    ))
                                ) : (
                                    <div className="px-4 py-3 text-sm text-brand-sage italic">No matches found</div>
                                )}
                            </div>
                        )}
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
                        onChange={(e) => {
                            const val = e.target.value || undefined
                            setFilters(prev => ({ ...prev, permit: val, utility_id: undefined }))
                        }}
                    />
                </div>

                {/* County Selection */}
                <div className="space-y-2" ref={countyRef}>
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">County</label>
                    <div className="relative group">
                        <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-brand-sage/60 group-focus-within:text-brand-teal transition-colors" />
                        <input
                            type="text"
                            className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg pl-10 pr-10 py-2.5 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all"
                            placeholder={filters.county || "Search county..."}
                            value={countySearch}
                            onFocus={() => setShowCountyDropdown(true)}
                            onChange={(e) => {
                                setCountySearch(e.target.value)
                                setShowCountyDropdown(true)
                            }}
                        />
                        <ChevronDown className="absolute right-3 top-2.5 h-4 w-4 text-brand-sage/40 pointer-events-none" />
                        {showCountyDropdown && (
                            <div className="absolute z-50 mt-1 w-full max-h-64 overflow-y-auto bg-white border border-brand-sage/20 rounded-lg shadow-xl py-1">
                                <button
                                    type="button"
                                    onClick={() => {
                                        handleChange('county', undefined)
                                        setCountySearch('')
                                        setShowCountyDropdown(false)
                                    }}
                                    className="w-full text-left px-4 py-2 text-sm hover:bg-brand-sage/5 transition-colors text-brand-teal font-bold"
                                >
                                    All Counties
                                </button>
                                {filteredCounties.length > 0 ? (
                                    filteredCounties.map(c => (
                                        <button
                                            key={c}
                                            type="button"
                                            onClick={() => {
                                                handleChange('county', c)
                                                setCountySearch('')
                                                setShowCountyDropdown(false)
                                            }}
                                            className="w-full text-left px-4 py-2 text-sm hover:bg-brand-sage/5 transition-colors border-b border-brand-sage/5 last:border-0 text-brand-charcoal"
                                        >
                                            {c}
                                        </button>
                                    ))
                                ) : (
                                    <div className="px-4 py-2 text-sm text-brand-sage italic">No matches found</div>
                                )}
                            </div>
                        )}
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

            <div className="flex justify-between items-center pt-2">
                <button
                    type="button"
                    onClick={handleReset}
                    className="text-brand-sage hover:text-brand-teal text-xs font-bold uppercase tracking-widest transition-colors flex items-center gap-2"
                >
                    <X className="w-3 h-3" />
                    Reset All Filters
                </button>
                <button
                    type="submit"
                    disabled={isLoading}
                    className="bg-brand-sage hover:bg-brand-sage/90 text-white text-sm font-heading font-bold px-8 py-3 rounded-lg shadow-sm hover:shadow-md transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-widest"
                >
                    {isLoading && <Loader2 className="w-4 h-4 animate-spin text-white" />}
                    Apply Filters
                </button>
            </div>
        </form>
    )
}
