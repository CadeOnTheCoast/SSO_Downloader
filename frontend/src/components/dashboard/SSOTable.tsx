import React, { useState, useMemo } from 'react'
import { SSORecord } from '@/lib/api'
import { ChevronUp, ChevronDown, ArrowUpDown } from 'lucide-react'

interface SSOTableProps {
    records: SSORecord[]
    page?: number
    onChangePage?: (newPage: number) => void
    hasNextPage?: boolean
    fullCsvUrl?: string
}

type SortConfig = {
    key: keyof SSORecord
    direction: 'asc' | 'desc'
}

export function SSOTable({ records, page = 1, onChangePage, hasNextPage = false, fullCsvUrl }: SSOTableProps) {
    const [sortConfig, setSortConfig] = useState<SortConfig | null>({
        key: 'volume_gallons',
        direction: 'desc'
    })

    const handleSort = (key: keyof SSORecord) => {
        let direction: 'asc' | 'desc' = 'asc'
        if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc'
        }
        setSortConfig({ key, direction })
    }

    const sortedRecords = useMemo(() => {
        if (!sortConfig) return records

        return [...records].sort((a, b) => {
            const aVal = a[sortConfig.key]
            const bVal = b[sortConfig.key]

            if (aVal === bVal) return 0
            if (aVal === null || aVal === undefined) return 1
            if (bVal === null || bVal === undefined) return -1

            if (typeof aVal === 'string' && typeof bVal === 'string') {
                return sortConfig.direction === 'asc'
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal)
            }

            return sortConfig.direction === 'asc'
                ? (aVal as any) - (bVal as any)
                : (bVal as any) - (aVal as any)
        })
    }, [records, sortConfig])

    if (!records.length) {
        return (
            <div className="rounded-lg border border-brand-sage/20 bg-white p-12 text-center shadow-sm">
                <p className="text-brand-sage/60 font-medium">No records found matching your criteria.</p>
            </div>
        )
    }

    const SortIcon = ({ column }: { column: keyof SSORecord }) => {
        if (sortConfig?.key !== column) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-20" />
        return sortConfig.direction === 'asc'
            ? <ChevronUp className="h-3 w-3 ml-1 text-brand-teal" />
            : <ChevronDown className="h-3 w-3 ml-1 text-brand-teal" />
    }

    return (
        <div className="space-y-4">
            <div className="rounded-lg border border-brand-sage/20 bg-white shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-brand-charcoal/80">
                        <thead className="bg-slate-50 text-brand-charcoal border-b border-brand-sage/10 font-heading font-bold text-xs tracking-widest uppercase">
                            <tr>
                                <th
                                    className="px-6 py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('utility_name')}
                                >
                                    <div className="flex items-center">Utility <SortIcon column="utility_name" /></div>
                                </th>
                                <th
                                    className="px-6 py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('county')}
                                >
                                    <div className="flex items-center">County <SortIcon column="county" /></div>
                                </th>
                                <th
                                    className="px-6 py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('date_sso_began')}
                                >
                                    <div className="flex items-center">Date <SortIcon column="date_sso_began" /></div>
                                </th>
                                <th
                                    className="px-6 py-4 text-right cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('volume_gallons')}
                                >
                                    <div className="flex items-center justify-end">Volume (Gal) <SortIcon column="volume_gallons" /></div>
                                </th>
                                <th
                                    className="px-6 py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('cause')}
                                >
                                    <div className="flex items-center">Cause <SortIcon column="cause" /></div>
                                </th>
                                <th
                                    className="px-6 py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('receiving_water')}
                                >
                                    <div className="flex items-center">Receiving Water <SortIcon column="receiving_water" /></div>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-brand-sage/5">
                            {sortedRecords.map((record) => {
                                const vol = record.volume_gallons ?? 0;
                                // Infographic Heatmap Coloring
                                let volClass = "text-brand-charcoal";
                                let bgClass = "";
                                if (vol > 100000) {
                                    volClass = "text-white font-bold";
                                    bgClass = "bg-brand-terracotta";
                                } else if (vol > 10000) {
                                    volClass = "text-white font-bold";
                                    bgClass = "bg-brand-ochre";
                                } else if (vol > 1000) {
                                    volClass = "text-brand-charcoal font-bold";
                                    bgClass = "bg-brand-mint/30";
                                }

                                return (
                                    <tr key={record.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-6 py-4 font-bold text-brand-charcoal">{record.utility_name}</td>
                                        <td className="px-6 py-4">{record.county}</td>
                                        <td className="px-6 py-4 font-mono text-xs">
                                            {record.date_sso_began ? new Date(record.date_sso_began).toLocaleDateString() : 'N/A'}
                                        </td>
                                        <td className={`px-6 py-4 text-right tabular-nums ${volClass} ${bgClass}`}>
                                            {vol.toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 max-w-[200px] truncate italic text-brand-charcoal/60" title={record.cause}>
                                            {record.cause}
                                        </td>
                                        <td className="px-6 py-4 max-w-[200px] truncate font-medium text-brand-sage" title={record.receiving_water}>
                                            {record.receiving_water}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {(onChangePage || fullCsvUrl) && (
                <div className="flex justify-between items-center px-4 py-2">
                    <div className="flex gap-6 items-center">
                        <button
                            onClick={() => onChangePage?.(Math.max(1, page - 1))}
                            disabled={page === 1}
                            className="text-xs font-heading font-bold tracking-widest uppercase text-brand-sage hover:text-brand-charcoal disabled:opacity-30 disabled:hover:text-brand-sage transition-colors"
                        >
                            Previous
                        </button>
                        <span className="text-xs font-bold text-brand-charcoal/40 uppercase tracking-tighter">Page {page}</span>
                        <button
                            onClick={() => onChangePage?.(page + 1)}
                            disabled={!hasNextPage}
                            className="text-xs font-heading font-bold tracking-widest uppercase text-brand-sage hover:text-brand-charcoal disabled:opacity-30 disabled:hover:text-brand-sage transition-colors"
                        >
                            Next
                        </button>
                    </div>

                    {fullCsvUrl && (
                        <a
                            href={fullCsvUrl}
                            className="text-xs font-heading font-bold tracking-widest uppercase text-brand-teal hover:text-brand-charcoal transition-colors underline underline-offset-4 decoration-brand-teal/30 hover:decoration-brand-teal"
                        >
                            Download full CSV
                        </a>
                    )}
                </div>
            )}
        </div>
    )
}
