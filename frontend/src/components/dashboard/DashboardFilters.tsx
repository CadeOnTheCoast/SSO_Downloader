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
    const [permitSearch, setPermitSearch] = useState('')
    const [countySearch, setCountySearch] = useState('')
    const [showUtilityDropdown, setShowUtilityDropdown] = useState(false)
    const [showPermitDropdown, setShowPermitDropdown] = useState(false)
    const [showCountyDropdown, setShowCountyDropdown] = useState(false)
    const utilityRef = useRef<HTMLDivElement>(null)
    const permitRef = useRef<HTMLDivElement>(null)
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
            if (permitRef.current && !permitRef.current.contains(event.target as Node)) {
                setShowPermitDropdown(false)
            }
            if (countyRef.current && !countyRef.current.contains(event.target as Node)) {
                setShowCountyDropdown(false)
            }
        }
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                setShowUtilityDropdown(false)
                setShowPermitDropdown(false)
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
        setPermitSearch('')
        setCountySearch('')
        setShowUtilityDropdown(false)
        setShowPermitDropdown(false)
        setShowCountyDropdown(false)
        onFilterChange(resetFilters)
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        onFilterChange(filters)
    }

    // Enhanced utility filtering (Name, Slug, ID, Aliases)
    const filteredUtilities = (options?.utilities.filter(u => {
        const query = utilitySearch.toLowerCase()
        if (!query) return true
        return u.name.toLowerCase().includes(query) ||
            u.slug.toLowerCase().includes(query) ||
            u.id.toLowerCase().includes(query) ||
            (u.aliases || []).some(a => a.toLowerCase().includes(query))
    }) || []).sort((a, b) => {
        const query = utilitySearch.toLowerCase()
        if (!query) return 0
        const aName = a.name.toLowerCase()
        const bName = b.name.toLowerCase()
        // Exact match params
        const aExact = aName === query || a.id.toLowerCase() === query || a.slug.toLowerCase() === query
        const bExact = bName === query || b.id.toLowerCase() === query || b.slug.toLowerCase() === query
        if (aExact && !bExact) return -1
        if (!aExact && bExact) return 1

        // Starts with params
        const aStarts = aName.startsWith(query)
        const bStarts = bName.startsWith(query)
        if (aStarts && !bStarts) return -1
        if (!aStarts && bStarts) return 1

        return 0
    }).slice(0, 50)

    // Suggestion logic for "Did you mean"
    const getSuggestion = () => {
        if (utilitySearch.length < 3 || filteredUtilities.length > 0 || !options) return null
        const query = utilitySearch.toLowerCase()
        // Simple heuristic: find utility that starts with the query, or closest match
        const suggestion = options.utilities.find(u =>
            u.name.toLowerCase().startsWith(query.slice(0, 3)) ||
            u.slug.toLowerCase().startsWith(query.slice(0, 3))
        )
        return suggestion
    }

    const suggestion = getSuggestion()

    // Permit ID filtering
    const filteredPermits = options?.utilities.filter(u => {
        const query = permitSearch.toLowerCase()
        if (!query) return false
        return u.id.toLowerCase().includes(query) ||
            u.slug.toLowerCase().includes(query) ||
            u.name.toLowerCase().includes(query)
    }).slice(0, 20) || []

    const filteredCounties = options?.counties.filter(c =>
        c.toLowerCase().includes(countySearch.toLowerCase())
    ) || []

    const selectedUtilityIds = filters.utility_ids || (filters.utility_id ? [filters.utility_id] : [])
    const selectedUtilities = options?.utilities.filter(u => selectedUtilityIds.includes(u.id)) || []

    const toggleUtility = (id: string) => {
        const current = new Set(selectedUtilityIds)
        if (current.has(id)) {
            current.delete(id)
        } else {
            current.add(id)
        }
        const nextIds = Array.from(current)

        setFilters(prev => ({
            ...prev,
            utility_ids: nextIds.length > 0 ? nextIds : undefined,
            utility_id: undefined,
            permit: undefined
        }))
        setUtilitySearch('')
    }

    const highlightMatch = (text: string, query: string) => {
        if (!query) return text
        const parts = text.split(new RegExp(`(${query})`, 'gi'))
        return (
            <span>
                {parts.map((part, i) =>
                    part.toLowerCase() === query.toLowerCase()
                        ? <span key={i} className="bg-brand-teal/20 text-brand-teal font-bold">{part}</span>
                        : part
                )}
            </span>
        )
    }

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
                            placeholder={selectedUtilityIds.length > 0 ? `${selectedUtilityIds.length} selected` : "Search permittee or permit id..."}
                            value={utilitySearch}
                            onFocus={() => setShowUtilityDropdown(true)}
                            onChange={(e) => {
                                setUtilitySearch(e.target.value)
                                setShowUtilityDropdown(true)
                            }}
                        />
                        {selectedUtilityIds.length > 0 && (
                            <button
                                type="button"
                                onClick={() => {
                                    setFilters(prev => ({ ...prev, utility_ids: undefined, utility_id: undefined, permit: undefined }))
                                    setUtilitySearch('')
                                }}
                                className="absolute right-3 top-2.5 text-brand-sage hover:text-brand-teal transition-colors"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        )}
                        {/* Selected Badges */}
                        {selectedUtilityIds.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-2">
                                {selectedUtilities.map(u => (
                                    <span key={u.id} className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-brand-teal/10 text-brand-teal text-xs font-bold border border-brand-teal/20">
                                        {u.name}
                                        <button
                                            type="button"
                                            onClick={() => toggleUtility(u.id)}
                                            className="hover:text-brand-charcoal ml-1"
                                        >
                                            <X className="h-3 w-3" />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                        {showUtilityDropdown && (
                            <div className="absolute z-50 mt-1 w-full max-h-64 overflow-y-auto bg-white border border-brand-sage/20 rounded-lg shadow-xl py-1">
                                {filteredUtilities.length > 0 ? (
                                    filteredUtilities.map(u => (
                                        <button
                                            key={u.id}
                                            type="button"
                                            onClick={() => toggleUtility(u.id)}
                                            className={`w-full text-left px-4 py-3 text-sm transition-colors border-b border-brand-sage/5 last:border-0 ${selectedUtilityIds.includes(u.id)
                                                ? 'bg-brand-teal/5 hover:bg-brand-teal/10'
                                                : 'hover:bg-brand-sage/5'
                                                }`}
                                        >
                                            <div className="flex justify-between items-start">
                                                <div className="flex flex-col">
                                                    <div className="flex items-center gap-2">
                                                        <div className={`font-bold ${selectedUtilityIds.includes(u.id) ? 'text-brand-teal' : 'text-brand-charcoal'}`}>
                                                            {highlightMatch(u.name, utilitySearch)}
                                                        </div>
                                                        {(u.permits || []).length > 1 && (
                                                            <span className="px-1.5 py-0.5 bg-brand-teal/10 text-brand-teal text-[9px] font-bold rounded uppercase tracking-tighter">
                                                                {u.permits.length} Permits
                                                            </span>
                                                        )}
                                                        {selectedUtilityIds.includes(u.id) && <span className="text-brand-teal ml-2">✓</span>}
                                                    </div>
                                                    {/* Show matched alias if different from canonical name */}
                                                    {utilitySearch.length > 1 && (u.aliases || []).find(a =>
                                                        a.toLowerCase().includes(utilitySearch.toLowerCase()) &&
                                                        a.toLowerCase() !== u.name.toLowerCase()
                                                    ) && (
                                                            <div className="text-[10px] text-brand-sage italic mt-0.5">
                                                                alias: "{highlightMatch((u.aliases || []).find(a => a.toLowerCase().includes(utilitySearch.toLowerCase()))!, utilitySearch)}"
                                                            </div>
                                                        )}
                                                </div>
                                                <div className="text-[10px] text-brand-teal font-mono bg-brand-teal/5 px-1.5 py-0.5 rounded">{highlightMatch(u.slug, utilitySearch)}</div>
                                            </div>
                                            <div className="mt-1 flex flex-wrap gap-1">
                                                {(u.permits || []).slice(0, 3).map(p => (
                                                    <span key={p} className="text-[10px] text-brand-sage font-mono bg-slate-100 px-1 rounded">
                                                        {highlightMatch(p, utilitySearch)}
                                                    </span>
                                                ))}
                                                {(u.permits || []).length > 3 && (
                                                    <span className="text-[9px] text-brand-sage/60 font-medium">+{(u.permits || []).length - 3} more</span>
                                                )}
                                            </div>
                                        </button>
                                    ))
                                ) : (
                                    <div className="px-4 py-4 text-sm text-brand-sage italic">
                                        No matches found.
                                        {suggestion && (
                                            <div className="mt-2 not-italic">
                                                Did you mean <button
                                                    type="button"
                                                    onClick={() => setUtilitySearch(suggestion.name)}
                                                    className="text-brand-teal hover:underline font-bold"
                                                >
                                                    {suggestion.name}
                                                </button>?
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Enhanced Permit ID Searchable Selection */}
                <div className="space-y-2" ref={permitRef}>
                    <label className="font-heading text-xs text-brand-charcoal/60 font-bold tracking-wider">Permit ID / Outfall</label>
                    <div className="relative group">
                        {/* Radio buttons for selected utilities (single or multi) */}
                        {selectedUtilities.length > 0 && selectedUtilities.some(u => (u.permits || []).length > 0) ? (
                            <div className="bg-slate-50 border border-brand-sage/20 rounded-lg p-3 space-y-3 max-h-60 overflow-y-auto">
                                <label className="flex items-center gap-2 text-sm cursor-pointer hover:bg-brand-sage/5 p-1 rounded">
                                    <input
                                        type="radio"
                                        name="permit_select"
                                        value=""
                                        checked={!filters.permit}
                                        onChange={() => setFilters(prev => ({ ...prev, permit: undefined }))}
                                        className="text-brand-teal focus:ring-brand-teal"
                                    />
                                    <span className={!filters.permit ? 'font-bold text-brand-teal' : 'text-brand-charcoal'}>All Selected Permits</span>
                                </label>

                                {selectedUtilities.map(util => (
                                    (util.permits || []).length > 0 && (
                                        <div key={util.id} className="space-y-1">
                                            {selectedUtilities.length > 1 && (
                                                <div className="text-[10px] uppercase font-bold text-brand-sage/60 ml-1 mt-2 mb-1">
                                                    {util.name}
                                                </div>
                                            )}
                                            {util.permits.map(pid => (
                                                <label key={pid} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-brand-sage/5 p-1 rounded ml-1">
                                                    <input
                                                        type="radio"
                                                        name="permit_select"
                                                        value={pid}
                                                        checked={filters.permit === pid}
                                                        onChange={() => setFilters(prev => ({ ...prev, permit: pid }))}
                                                        className="text-brand-teal focus:ring-brand-teal"
                                                    />
                                                    <span className="font-mono text-xs">{pid}</span>
                                                </label>
                                            ))}
                                        </div>
                                    )
                                ))}
                            </div>
                        ) : (
                            // Standard Search Input
                            <>
                                <input
                                    type="text"
                                    className="w-full bg-slate-50 border border-brand-sage/20 rounded-lg px-3 py-2.5 text-sm text-brand-charcoal focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal transition-all uppercase placeholder:text-brand-sage/30"
                                    placeholder={filters.permit || "Search by permit/slug..."}
                                    value={permitSearch}
                                    onFocus={() => setShowPermitDropdown(true)}
                                    onChange={(e) => {
                                        setPermitSearch(e.target.value)
                                        setShowPermitDropdown(true)
                                        // Removed setFilters on keystroke to prevent lag/wonkiness
                                    }}
                                />
                                {showPermitDropdown && permitSearch.length > 0 && (
                                    <div className="absolute z-50 mt-1 w-full max-h-64 overflow-y-auto bg-white border border-brand-sage/20 rounded-lg shadow-xl py-1">
                                        {filteredPermits.length > 0 ? (
                                            filteredPermits.map(u => (
                                                <button
                                                    key={u.id}
                                                    type="button"
                                                    onClick={() => {
                                                        setFilters(prev => ({ ...prev, permit: u.id, utility_id: undefined, utility_ids: undefined }))
                                                        setPermitSearch('')
                                                        setShowPermitDropdown(false)
                                                    }}
                                                    className="w-full text-left px-4 py-3 text-sm hover:bg-brand-sage/5 transition-colors border-b border-brand-sage/5 last:border-0"
                                                >
                                                    <div className="font-mono text-xs font-bold text-brand-teal">{highlightMatch(u.id, permitSearch)}</div>
                                                    <div className="text-[10px] text-brand-sage truncate">{highlightMatch(u.name, permitSearch)}</div>
                                                    <div className="text-[9px] text-brand-sage/60 font-mono italic">{highlightMatch(u.slug, permitSearch)}</div>
                                                </button>
                                            ))
                                        ) : (
                                            <div className="px-4 py-3 text-sm text-brand-sage italic">No matches found</div>
                                        )}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
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
