'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "./Card"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line, PieChart, Pie, Cell, Legend } from "recharts"
import { SeriesPoint, BarGroup } from "@/lib/api"

interface SSOChartsProps {
    timeSeries: SeriesPoint[]
    barGroups: BarGroup[]
    receivingWaters?: { name: string, total_volume: number, spills: number }[]
    onPieClick?: (utilityName: string) => void
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

function getUtilitySlug(name: string): string {
    return name
        .replace(/Board|Commission|Authority|Utilities|Utility|Water|Sewer|Works|Board of/gi, '')
        .trim()
        .substring(0, 15);
}

export function SSOCharts({ timeSeries, barGroups, receivingWaters, onPieClick }: SSOChartsProps) {
    const showTimeSeries = timeSeries && timeSeries.length > 0;
    const totalVolume = barGroups.reduce((acc, curr) => acc + curr.total_volume_gallons, 0);

    return (
        <div className="grid gap-6 md:grid-cols-2">
            {/* Time Series Chart */}
            <Card className="col-span-2 text-white border-slate-800 bg-slate-900/50">
                <CardHeader>
                    <CardTitle className="text-slate-200 text-lg">Spills Over Time</CardTitle>
                </CardHeader>
                <CardContent className="pl-2">
                    {showTimeSeries ? (
                        <div className="h-[300px] min-h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={timeSeries}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                    <XAxis
                                        dataKey="date"
                                        stroke="#64748b"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        stroke="#64748b"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                                        itemStyle={{ color: '#e2e8f0' }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="count"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        dot={false}
                                        activeDot={{ r: 4 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div className="h-[300px] flex items-center justify-center bg-slate-900/10 rounded-lg">
                            <p className="text-slate-500 italic text-sm">No time-series data available for this range.</p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Volume by Utility (Bar Chart) */}
            <Card className="col-span-1 text-white border-slate-800 bg-slate-900/50">
                <CardHeader>
                    <CardTitle className="text-slate-200 text-lg">Volume by Utility (Top 10)</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] min-h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={barGroups.slice(0, 10)} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                                <XAxis type="number" hide />
                                <YAxis
                                    dataKey="label"
                                    type="category"
                                    width={120}
                                    stroke="#64748b"
                                    fontSize={10}
                                    tickLine={false}
                                    axisLine={false}
                                    tickFormatter={(value) => getUtilitySlug(value || '')}
                                />
                                <Tooltip
                                    cursor={{ fill: '#1e293b' }}
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                                    itemStyle={{ color: '#e2e8f0' }}
                                    formatter={(value: any, name: any, props: any) => [
                                        `${(value ?? 0).toLocaleString()} gal`,
                                        props.payload.label || 'Unknown'
                                    ]}
                                />
                                <Bar dataKey="total_volume_gallons" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* High Volume Sources (Pie Chart) */}
            <Card className="col-span-1 text-white border-slate-800 bg-slate-900/50">
                <CardHeader>
                    <CardTitle className="text-slate-200 text-lg">Volume Share</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] min-h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={barGroups.slice(0, 5)}
                                    dataKey="total_volume_gallons"
                                    nameKey="label"
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={80}
                                    fill="#8884d8"
                                    onClick={(data) => onPieClick && onPieClick(data.label)}
                                    cursor="pointer"
                                    label={({ name, percent }) => `${getUtilitySlug(name || '')} ${((percent || 0) * 100).toFixed(0)}%`}
                                >
                                    {barGroups.slice(0, 5).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                                    itemStyle={{ color: '#e2e8f0' }}
                                    formatter={(value: any, name: any) => {
                                        const pct = totalVolume > 0 ? ((value / totalVolume) * 100).toFixed(1) : 0;
                                        return [`${(value ?? 0).toLocaleString()} gal (${pct}%)`, name || 'Unknown'];
                                    }}
                                />
                                <Legend
                                    verticalAlign="bottom"
                                    height={36}
                                    wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }}
                                    formatter={(value) => getUtilitySlug(value || '')}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* Top Receiving Waters (Bar Chart) */}
            <Card className="col-span-1 text-white border-slate-800 bg-slate-900/50">
                <CardHeader>
                    <CardTitle className="text-slate-200 text-lg">Top Receiving Waters</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] min-h-[300px] w-full">
                        {receivingWaters && receivingWaters.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={receivingWaters.slice(0, 10)} layout="vertical">
                                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                                    <XAxis type="number" hide />
                                    <YAxis
                                        dataKey="name"
                                        type="category"
                                        width={150}
                                        stroke="#64748b"
                                        fontSize={10}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(value) => value.length > 25 ? `${value.substring(0, 22)}...` : value}
                                    />
                                    <Tooltip
                                        cursor={{ fill: '#1e293b' }}
                                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                                        itemStyle={{ color: '#e2e8f0' }}
                                        formatter={(value: any) => `${(value ?? 0).toLocaleString()} gal`}
                                    />
                                    <Bar dataKey="total_volume" fill="#10b981" radius={[0, 4, 4, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <p className="text-slate-500 text-sm italic">No volume data to chart for receiving waters.</p>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Receiving Water Impact (Table) */}
            <Card className="col-span-1 text-white border-slate-800 bg-slate-900/50 overflow-hidden">
                <CardHeader>
                    <CardTitle className="text-slate-200 text-lg">Receiving Water Impact</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-slate-400">
                            <thead className="bg-slate-800/50 text-slate-300">
                                <tr>
                                    <th className="px-4 py-2 font-medium">Water Body</th>
                                    <th className="px-4 py-2 font-medium text-right">Spills</th>
                                    <th className="px-4 py-2 font-medium text-right">Volume (Gal)</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {receivingWaters && receivingWaters.length > 0 ? (
                                    receivingWaters.slice(0, 8).map((rw, idx) => (
                                        <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                                            <td className="px-4 py-2 text-slate-200 font-medium truncate max-w-[140px]" title={rw.name}>
                                                {rw.name}
                                            </td>
                                            <td className="px-4 py-2 text-right">{rw.spills}</td>
                                            <td className="px-4 py-2 text-right">{(rw.total_volume ?? 0).toLocaleString()}</td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan={3} className="px-4 py-8 text-center text-slate-500">
                                            No receiving water data available.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
