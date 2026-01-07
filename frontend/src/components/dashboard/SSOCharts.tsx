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

const COLORS = ['#6B8982', '#4AA0AF', '#8CCAAE', '#A2D3F3', '#35403A', '#BA4A3E'];
const TEXT_COLOR = '#35403A';
const GRID_COLOR = '#E2E8E7'; // Light sage-tinted grid

const getUtilitySlug = (name: string): string => {
    if (!name) return '';
    // Simple truncation for chart labels
    return name.length > 20 ? name.substring(0, 20) + '...' : name;
};



export function SSOCharts({ timeSeries, barGroups, receivingWaters, onPieClick }: SSOChartsProps) {
    console.log("Rendering SSOCharts with new slug logic");
    const showTimeSeries = timeSeries && timeSeries.length > 0;
    const totalVolume = barGroups.reduce((acc, curr) => acc + curr.total_volume_gallons, 0);

    return (
        <div className="grid gap-4 md:grid-cols-2">
            {/* Time Series Chart */}
            <Card className="col-span-1 md:col-span-2 border-brand-sage/10 shadow-sm">
                <CardHeader className="p-4 md:p-6 pb-2 md:pb-4">
                    <CardTitle className="text-brand-charcoal text-base md:text-lg font-bold">Spills Over Time</CardTitle>
                </CardHeader>
                <CardContent className="p-0 md:p-6 pl-0">
                    {showTimeSeries ? (
                        <div className="h-[250px] md:h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={timeSeries} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                                    <defs>
                                        <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#BA4A3E" stopOpacity={0.8} />
                                            <stop offset="50%" stopColor="#DAA520" stopOpacity={0.6} />
                                            <stop offset="100%" stopColor="#4AA0AF" stopOpacity={0.8} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                                    <XAxis
                                        dataKey="date"
                                        stroke={TEXT_COLOR}
                                        fontSize={10}
                                        tickLine={false}
                                        axisLine={false}
                                        className="font-sans"
                                    />
                                    <YAxis
                                        stroke={TEXT_COLOR}
                                        fontSize={10}
                                        tickLine={false}
                                        axisLine={false}
                                        className="font-sans"
                                        width={30}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#ffffff', borderColor: '#E2E8E7', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                        itemStyle={{ color: TEXT_COLOR, fontWeight: 600, fontSize: '12px' }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="count"
                                        stroke="url(#lineGradient)"
                                        strokeWidth={3}
                                        dot={false}
                                        activeDot={{ r: 6, fill: '#BA4A3E', strokeWidth: 2, stroke: '#fff' }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div className="h-[250px] md:h-[300px] flex items-center justify-center bg-slate-50 rounded-lg border border-dashed border-slate-200 m-4">
                            <p className="text-slate-400 italic text-xs md:text-sm">No time-series data available for this range.</p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Volume by Utility (Bar Chart) */}
            <Card className="col-span-1 border-brand-sage/10 shadow-sm">
                <CardHeader className="p-4 md:p-6 pb-2 md:pb-4">
                    <CardTitle className="text-brand-charcoal text-base md:text-lg font-bold">Volume by Utility (Top 10)</CardTitle>
                </CardHeader>
                <CardContent className="p-4 md:p-6 pt-0 md:pt-0">
                    <div className="h-[300px] min-h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={barGroups.slice(0, 10)} layout="vertical" margin={{ top: 0, right: 0, left: 10, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} horizontal={false} />
                                <XAxis type="number" hide />
                                <YAxis
                                    dataKey="label"
                                    type="category"
                                    width={100}
                                    stroke={TEXT_COLOR}
                                    fontSize={9}
                                    tickLine={false}
                                    axisLine={false}
                                    tickFormatter={(value) => value}
                                    className="font-medium"
                                />
                                <Tooltip
                                    cursor={{ fill: '#F8F9FB' }}
                                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#E2E8E7', borderRadius: '8px' }}
                                    itemStyle={{ color: TEXT_COLOR, fontWeight: 600, fontSize: '12px' }}
                                    formatter={(value: any) => [
                                        `${(value ?? 0).toLocaleString()} gal`,
                                        "Volume"
                                    ]}
                                />
                                <Bar dataKey="total_volume_gallons" radius={[0, 4, 4, 0]}>
                                    {barGroups.slice(0, 10).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* High Volume Sources (Pie Chart) */}
            <Card className="col-span-1 border-brand-sage/10 shadow-sm">
                <CardHeader className="p-4 md:p-6 pb-2 md:pb-4">
                    <CardTitle className="text-brand-charcoal text-base md:text-lg font-bold">Volume Share</CardTitle>
                </CardHeader>
                <CardContent className="p-0 md:p-6">
                    <div className="h-[250px] md:h-[300px] min-h-[250px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={barGroups.slice(0, 5)}
                                    dataKey="total_volume_gallons"
                                    nameKey="label"
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={70}
                                    fill="#8884d8"
                                    onClick={(data) => onPieClick && onPieClick(data.label)}
                                    cursor="pointer"
                                    label={({ name, percent }) => `${getUtilitySlug(name || '')} ${((percent || 0) * 100).toFixed(0)}%`}
                                    labelLine={false}
                                >
                                    {barGroups.slice(0, 5).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#E2E8E7', borderRadius: '8px' }}
                                    itemStyle={{ color: TEXT_COLOR, fontWeight: 600, fontSize: '12px' }}
                                    formatter={(value: any, name: any) => {
                                        const pct = totalVolume > 0 ? ((value / totalVolume) * 100).toFixed(1) : 0;
                                        return [`${(value ?? 0).toLocaleString()} gal (${pct}%)`, name || 'Unknown'];
                                    }}
                                />
                                <Legend
                                    verticalAlign="bottom"
                                    height={36}
                                    wrapperStyle={{ fontSize: '10px', paddingTop: '10px', fontFamily: 'Montserrat' }}
                                    formatter={(value) => getUtilitySlug(value || '')}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* Top Receiving Waters (Bar Chart) */}
            <Card className="col-span-1 border-brand-sage/10 shadow-sm">
                <CardHeader className="p-4 md:p-6 pb-2 md:pb-4">
                    <CardTitle className="text-brand-charcoal text-base md:text-lg font-bold">Top Receiving Waters</CardTitle>
                </CardHeader>
                <CardContent className="p-4 md:p-6 pt-0 md:pt-0">
                    <div className="h-[300px] min-h-[300px] w-full">
                        {receivingWaters && receivingWaters.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={receivingWaters.slice(0, 10)} layout="vertical" margin={{ top: 0, right: 0, left: 10, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} horizontal={false} />
                                    <XAxis type="number" hide />
                                    <YAxis
                                        dataKey="name"
                                        type="category"
                                        width={120}
                                        stroke={TEXT_COLOR}
                                        fontSize={9}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(value) => value}
                                        className="font-medium"
                                    />
                                    <Tooltip
                                        cursor={{ fill: '#F8F9FB' }}
                                        contentStyle={{ backgroundColor: '#ffffff', borderColor: '#E2E8E7', borderRadius: '8px' }}
                                        itemStyle={{ color: TEXT_COLOR, fontWeight: 600, fontSize: '12px' }}
                                        formatter={(value: any) => [
                                            `${(value ?? 0).toLocaleString()} gal`,
                                            "Volume"
                                        ]}
                                    />
                                    <Bar dataKey="total_volume" radius={[0, 4, 4, 0]}>
                                        {receivingWaters.slice(0, 10).map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <p className="text-slate-400 text-sm italic">No volume data to chart for receiving waters.</p>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Receiving Water Impact (Table) */}
            <Card className="col-span-1 border-brand-sage/10 shadow-sm overflow-hidden">
                <CardHeader className="p-4 md:p-6">
                    <CardTitle className="text-brand-charcoal text-base md:text-lg font-bold">Receiving Water Impact</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-brand-charcoal/80">
                            <thead className="bg-slate-50 text-brand-charcoal border-b border-brand-sage/10">
                                <tr>
                                    <th className="px-4 py-3 font-heading font-bold text-[10px] md:text-xs tracking-wider">Water Body</th>
                                    <th className="px-4 py-3 font-heading font-bold text-[10px] md:text-xs tracking-wider text-right">Spills</th>
                                    <th className="px-4 py-3 font-heading font-bold text-[10px] md:text-xs tracking-wider text-right">Volume (Gal)</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-brand-sage/5">
                                {receivingWaters && receivingWaters.length > 0 ? (
                                    receivingWaters.slice(0, 8).map((rw, idx) => (
                                        <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                                            <td className="px-4 py-3 text-brand-charcoal font-medium truncate max-w-[120px] md:max-w-[140px] text-xs md:text-sm" title={rw.name}>
                                                {rw.name}
                                            </td>
                                            <td className="px-4 py-3 text-right font-mono text-xs md:text-sm">{rw.spills}</td>
                                            <td className="px-4 py-3 text-right font-bold text-brand-sage text-xs md:text-sm">{(rw.total_volume ?? 0).toLocaleString()}</td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan={3} className="px-4 py-8 text-center text-slate-500 text-xs md:text-sm">
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
