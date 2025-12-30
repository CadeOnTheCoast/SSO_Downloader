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
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center">
                <p className="text-slate-400">No records found matching your criteria.</p>
            </div>
        )
    }

    const SortIcon = ({ column }: { column: keyof SSORecord }) => {
        if (sortConfig?.key !== column) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-20" />
        return sortConfig.direction === 'asc'
            ? <ChevronUp className="h-3 w-3 ml-1 text-blue-400" />
            : <ChevronDown className="h-3 w-3 ml-1 text-blue-400" />
    }

    return (
        <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-slate-400">
                        <thead className="bg-slate-900 text-slate-200">
                            <tr>
                                <th
                                    className="px-6 py-3 font-medium cursor-pointer hover:bg-slate-800 transition-colors"
                                    onClick={() => handleSort('utility_name')}
                                >
                                    <div className="flex items-center">Utility <SortIcon column="utility_name" /></div>
                                </th>
                                <th
                                    className="px-6 py-3 font-medium cursor-pointer hover:bg-slate-800 transition-colors"
                                    onClick={() => handleSort('county')}
                                >
                                    <div className="flex items-center">County <SortIcon column="county" /></div>
                                </th>
                                <th
                                    className="px-6 py-3 font-medium cursor-pointer hover:bg-slate-800 transition-colors"
                                    onClick={() => handleSort('date_sso_began')}
                                >
                                    <div className="flex items-center">Date <SortIcon column="date_sso_began" /></div>
                                </th>
                                <th
                                    className="px-6 py-3 font-medium text-right cursor-pointer hover:bg-slate-800 transition-colors"
                                    onClick={() => handleSort('volume_gallons')}
                                >
                                    <div className="flex items-center justify-end">Volume (Gal) <SortIcon column="volume_gallons" /></div>
                                </th>
                                <th
                                    className="px-6 py-3 font-medium cursor-pointer hover:bg-slate-800 transition-colors"
                                    onClick={() => handleSort('cause')}
                                >
                                    <div className="flex items-center">Cause <SortIcon column="cause" /></div>
                                </th>
                                <th
                                    className="px-6 py-3 font-medium cursor-pointer hover:bg-slate-800 transition-colors"
                                    onClick={() => handleSort('receiving_water')}
                                >
                                    <div className="flex items-center">Receiving Water <SortIcon column="receiving_water" /></div>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {sortedRecords.map((record) => (
                                <tr key={record.id} className="hover:bg-slate-800/50 transition-colors">
                                    <td className="px-6 py-4 font-medium text-white">{record.utility_name}</td>
                                    <td className="px-6 py-4">{record.county}</td>
                                    <td className="px-6 py-4">
                                        {record.date_sso_began ? new Date(record.date_sso_began).toLocaleDateString() : 'N/A'}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        {(record.volume_gallons ?? 0).toLocaleString()}
                                    </td>
                                    <td className="px-6 py-4 max-w-[200px] truncate" title={record.cause}>
                                        {record.cause}
                                    </td>
                                    <td className="px-6 py-4 max-w-[200px] truncate" title={record.receiving_water}>
                                        {record.receiving_water}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {(onChangePage || fullCsvUrl) && (
                <div className="flex justify-between items-center px-2">
                    <div className="flex gap-4 items-center">
                        <button
                            onClick={() => onChangePage?.(Math.max(1, page - 1))}
                            disabled={page === 1}
                            className="text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400"
                        >
                            Previous
                        </button>
                        <span className="text-sm text-slate-500">Page {page}</span>
                        <button
                            onClick={() => onChangePage?.(page + 1)}
                            disabled={!hasNextPage}
                            className="text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400"
                        >
                            Next
                        </button>
                    </div>

                    {fullCsvUrl && (
                        <a
                            href={fullCsvUrl}
                            className="text-sm text-blue-400 hover:text-blue-300 font-medium transition-colors"
                        >
                            Download full CSV
                        </a>
                    )}
                </div>
            )}
        </div>
    )
}
