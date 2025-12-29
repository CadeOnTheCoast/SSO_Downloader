'use client'

import React from 'react'
import { SSORecord } from '@/lib/api'

interface SSOTableProps {
    records: SSORecord[]
    page?: number
    onChangePage?: (newPage: number) => void
    hasNextPage?: boolean
}

export function SSOTable({ records, page = 1, onChangePage, hasNextPage = false }: SSOTableProps) {
    if (!records.length) {
        return (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center">
                <p className="text-slate-400">No records found matching your criteria.</p>
            </div>
        )
    }

    return (
        <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-slate-400">
                        <thead className="bg-slate-900 text-slate-200">
                            <tr>
                                <th className="px-6 py-3 font-medium">Utility</th>
                                <th className="px-6 py-3 font-medium">County</th>
                                <th className="px-6 py-3 font-medium">Date</th>
                                <th className="px-6 py-3 font-medium text-right">Volume (Gal)</th>
                                <th className="px-6 py-3 font-medium">Cause</th>
                                <th className="px-6 py-3 font-medium">Receiving Water</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {records.map((record) => (
                                <tr key={record.id} className="hover:bg-slate-800/50 transition-colors">
                                    <td className="px-6 py-4 font-medium text-white">{record.utility_name}</td>
                                    <td className="px-6 py-4">{record.county}</td>
                                    <td className="px-6 py-4">
                                        {record.date_sso_began ? new Date(record.date_sso_began).toLocaleDateString() : 'N/A'}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        {record.volume_gallons?.toLocaleString()}
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

            {(onChangePage) && (
                <div className="flex justify-between items-center px-2">
                    <button
                        onClick={() => onChangePage(Math.max(1, page - 1))}
                        disabled={page === 1}
                        className="text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400"
                    >
                        Previous
                    </button>
                    <span className="text-sm text-slate-500">Page {page}</span>
                    <button
                        onClick={() => onChangePage(page + 1)}
                        disabled={!hasNextPage}
                        className="text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400"
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    )
}
