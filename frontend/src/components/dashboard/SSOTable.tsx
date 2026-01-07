import React, { useState, useMemo } from 'react'
import { SSORecord } from '@/lib/api'
import { ChevronUp, ChevronDown, ArrowUpDown } from 'lucide-react'

interface SSOTableProps {
    records: SSORecord[]
    page?: number
    onChangePage?: (newPage: number) => void
    onSortChange?: (key: string, direction: 'asc' | 'desc') => void
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
    hasNextPage?: boolean
    fullCsvUrl?: string
}

type SortConfig = {
    key: keyof SSORecord
    direction: 'asc' | 'desc'
}

export function SSOTable({
    records,
    page = 1,
    onChangePage,
    onSortChange,
    sortBy = 'volume_gallons',
    sortOrder = 'desc',
    hasNextPage = false,
    fullCsvUrl
}: SSOTableProps) {
    const handleSort = (key: keyof SSORecord) => {
        const newDirection: 'asc' | 'desc' =
            sortBy === key && sortOrder === 'asc' ? 'desc' : 'asc'
        onSortChange?.(key, newDirection)
    }


    if (!records.length) {
        return (
            <div className="rounded-lg border border-brand-sage/20 bg-white p-12 text-center shadow-sm">
                <p className="text-brand-sage/60 font-medium">No records found matching your criteria.</p>
            </div>
        )
    }

    const SortIcon = ({ column }: { column: keyof SSORecord }) => {
        if (sortBy !== column) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-20" />
        return sortOrder === 'asc'
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
                                    className="px-4 md:px-6 py-3 md:py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('utility_name')}
                                >
                                    <div className="flex items-center">Utility <SortIcon column="utility_name" /></div>
                                </th>
                                <th
                                    className="hidden md:table-cell px-6 py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('county')}
                                >
                                    <div className="flex items-center">County <SortIcon column="county" /></div>
                                </th>
                                <th
                                    className="px-4 md:px-6 py-3 md:py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('date_sso_began')}
                                >
                                    <div className="flex items-center">Date <SortIcon column="date_sso_began" /></div>
                                </th>
                                <th
                                    className="px-4 md:px-6 py-3 md:py-4 text-right cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('volume_gallons')}
                                >
                                    <div className="flex items-center justify-end">Volume (Gal) <SortIcon column="volume_gallons" /></div>
                                </th>
                                <th className="hidden md:table-cell px-6 py-4">
                                    <div className="flex items-center text-brand-sage/80 cursor-default">Location</div>
                                </th>
                                <th
                                    className="px-4 md:px-6 py-3 md:py-4 cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => handleSort('receiving_water')}
                                >
                                    <div className="flex items-center">Receiving Water <SortIcon column="receiving_water" /></div>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-brand-sage/5">
                            {records.map((record) => {
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
                                        <td className="px-4 md:px-6 py-3 md:py-4 font-bold text-brand-charcoal md:whitespace-nowrap min-w-[120px] md:min-w-0 text-xs md:text-sm">{record.utility_name}</td>
                                        <td className="hidden md:table-cell px-6 py-4">{record.county}</td>
                                        <td className="px-4 md:px-6 py-3 md:py-4 font-mono text-xs md:whitespace-nowrap">
                                            {record.date_sso_began ? new Date(record.date_sso_began).toLocaleDateString() : 'N/A'}
                                        </td>
                                        <td className={`px-4 md:px-6 py-3 md:py-4 text-right tabular-nums ${volClass} ${bgClass} text-xs md:text-sm`}>
                                            {vol.toLocaleString()}
                                        </td>
                                        <td className="hidden md:table-cell px-6 py-4 whitespace-nowrap">
                                            {record.latitude && record.longitude ? (
                                                <a
                                                    href={`https://www.google.com/maps/search/?api=1&query=${record.latitude},${record.longitude}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-brand-teal hover:underline font-mono text-xs"
                                                >
                                                    {record.latitude.toFixed(4)}, {record.longitude.toFixed(4)}
                                                </a>
                                            ) : (
                                                <span className="text-brand-sage/40 text-xs">N/A</span>
                                            )}
                                        </td>
                                        <td className="px-4 md:px-6 py-3 md:py-4 max-w-[150px] md:max-w-[200px] truncate font-medium text-brand-sage text-xs md:text-sm" title={record.receiving_water}>
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
