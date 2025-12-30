'use client'

import { Card, CardContent, CardHeader, CardTitle } from "./Card"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line, PieChart, Pie, Cell, Legend } from "recharts"
import { SeriesPoint, BarGroup } from "@/lib/api"
import type { ValueType } from "recharts/types/component/DefaultTooltipContent"

interface SSOChartsProps {
    timeSeries: SeriesPoint[]
    barGroups: BarGroup[]
    pieData?: { name: string, value: number }[]
    onPieClick?: (utilityName: string) => void
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export function SSOCharts({ timeSeries, barGroups, pieData, onPieClick }: SSOChartsProps) {
    return (
        <div className="grid gap-4 md:grid-cols-2">
            {/* Time Series Chart */}
            <Card className="col-span-2 text-white">
                <CardHeader>
                    <CardTitle className="text-slate-200 text-lg">Spills Over Time</CardTitle>
                </CardHeader>
                <CardContent className="pl-2">
                    <div className="h-[300px] w-full">
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
                                    tickFormatter={(value) => `${value}`}
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
                </CardContent>
            </Card>

            {/* Volume by Utility (Bar Chart) */}
            <Card className="col-span-1 text-white">
                <CardHeader>
                    <CardTitle className="text-slate-200 text-lg">Volume by Utility (Top 10)</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={barGroups.slice(0, 10)} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                                <XAxis type="number" hide />
                                <YAxis
                                    dataKey="label"
                                    type="category"
                                    width={100}
                                    stroke="#64748b"
                                    fontSize={11}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <Tooltip
                                    cursor={{ fill: '#1e293b' }}
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                                    itemStyle={{ color: '#e2e8f0' }}
                                    formatter={(value: any) => value.toLocaleString()}
                                />
                                <Bar dataKey="total_volume_gallons" fill="#10b981" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* Top Utilities by Volume (Pie Chart) - Interactive */}
            <Card className="col-span-1 text-white">
                <CardHeader>
                    <CardTitle className="text-slate-200 text-lg">High Volume Sources</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] w-full">
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
                                    label
                                    onClick={(data) => onPieClick && onPieClick(data.label)}
                                    cursor="pointer"
                                >
                                    {barGroups.slice(0, 5).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                                    itemStyle={{ color: '#e2e8f0' }}
                                    formatter={(value?: ValueType) => {
                                        if (Array.isArray(value)) {
                                            const firstValue = value[0]
                                            if (typeof firstValue === 'number') {
                                                return `${firstValue.toLocaleString()} gal`
                                            }

                                            if (typeof firstValue === 'string') {
                                                const numeric = Number(firstValue)
                                                return `${Number.isNaN(numeric) ? firstValue : numeric.toLocaleString()} gal`
                                            }

                                            return '0 gal'
                                        }

                                        if (typeof value === 'number') {
                                            return `${value.toLocaleString()} gal`
                                        }

                                        if (typeof value === 'string') {
                                            const numeric = Number(value)
                                            return `${Number.isNaN(numeric) ? value : numeric.toLocaleString()} gal`
                                        }

                                        return '0 gal'
                                    }}
                                />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
