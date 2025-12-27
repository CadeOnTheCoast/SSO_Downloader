"use client"


import { Droplets, AlertTriangle, Building, MapPin } from "lucide-react"

interface StatsProps {
    totalSsos: number
    totalVolume: number
    uniqueUtilities: number
    topCounty: string
}

export function SSOOverview({ totalSsos, totalVolume, uniqueUtilities, topCounty }: StatsProps) {
    const stats = [
        { title: "Total SSOs", value: totalSsos, icon: AlertTriangle, color: "text-red-500" },
        { title: "Total Volume (Gal)", value: totalVolume.toLocaleString(), icon: Droplets, color: "text-blue-500" },
        { title: "Active Utilities", value: uniqueUtilities, icon: Building, color: "text-amber-500" },
        { title: "Most Active County", value: topCounty, icon: MapPin, color: "text-purple-500" },
    ]

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
                <div key={stat.title} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
                    <div className="flex items-center justify-between space-y-0 pb-2">
                        <h3 className="text-sm font-medium text-slate-400">{stat.title}</h3>
                        <stat.icon className={`h-4 w-4 ${stat.color}`} />
                    </div>
                    <div className="text-2xl font-bold text-white">{stat.value}</div>
                </div>
            ))}
        </div>
    )
}
