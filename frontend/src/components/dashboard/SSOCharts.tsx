"use client"

import {
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line, PieChart, Pie, Cell, Legend } from "recharts"
import { SeriesPoint, BarGroup } from "@/lib/api"

interface SeriesPoint {
    date: string;
    count: number;
}

interface BarGroup {
    label: string;
    total_volume_gallons: number;
}

interface SSOChartsProps {
    timeSeries: SeriesPoint[]
    barGroups: BarGroup[]
    pieData?: { name: string, value: number }[] // For top utilities or similar
    onPieClick?: (utilityName: string) => void
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export function SSOCharts({ timeSeries, barGroups, pieData, onPieClick }: SSOChartsProps) {
    return (
        <div className="grid gap-4 md:grid-cols-2">
            {/* Time Series Chart */}
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
            <XAxis type="number" hide />
            <YAxis
                dataKey="name"
                type="category"
                stroke="#94a3b8"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                width={100}
            />
            <Tooltip
                contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                cursor={{ fill: "#1e293b" }}
            />
            <Bar dataKey="total" fill="#38bdf8" radius={[0, 4, 4, 0]}>
                {countyData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? "#f43f5e" : "#38bdf8"} />
                ))}
            </Bar>
        </BarChart>
                    </ResponsiveContainer >
                </div >
            </div >
        </div >
    )
}
