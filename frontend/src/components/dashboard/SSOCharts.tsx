"use client"

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    LineChart,
    Line,
    Cell
} from "recharts"

interface ChartData {
    name: string
    total: number
}

interface SSOChartsProps {
    timeSeries: ChartData[]
    countyData: ChartData[]
}

export function SSOCharts({ timeSeries, countyData }: SSOChartsProps) {
    return (
        <div className="grid gap-4 md:grid-cols-2">
            {/* Time Series Chart */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-white mb-4">SSO Trend (Monthly)</h3>
                <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={timeSeries}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                            <XAxis
                                dataKey="name"
                                stroke="#94a3b8"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                                itemStyle={{ color: "#38bdf8" }}
                            />
                            <Line
                                type="monotone"
                                dataKey="total"
                                stroke="#38bdf8"
                                strokeWidth={2}
                                dot={{ fill: "#38bdf8", strokeWidth: 2 }}
                                activeDot={{ r: 6, fill: "#38bdf8" }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* County Bar Chart */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-white mb-4">SSOs by County (Top 10)</h3>
                <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={countyData} layout="vertical">
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
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    )
}
