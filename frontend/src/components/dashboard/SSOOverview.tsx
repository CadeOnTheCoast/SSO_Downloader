'use client'

import React from 'react'
import { Droplets, Activity, Building2, MapPin, AlertTriangle } from 'lucide-react'
import { Card } from './Card'
import { DashboardSummary } from '@/lib/api'

function StatCard({ title, value, icon: Icon, subtext }: { title: string, value: string | number, icon: any, subtext?: string }) {
    return (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div className="flex flex-row items-center justify-between pb-2">
                <h3 className="text-sm font-medium text-slate-400">{title}</h3>
                <Icon className="h-4 w-4 text-slate-500" />
            </div>
            <div>
                <div className="text-2xl font-bold text-white">{value}</div>
                {subtext && <p className="text-xs text-slate-500 mt-1">{subtext}</p>}
            </div>
        </div>
    )
}

interface SSOOverviewProps {
    summary: DashboardSummary | null
}

export function SSOOverview({ summary }: SSOOverviewProps) {
    if (!summary) return null;

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatCard
                title="Total Spills"
                value={summary.total_count}
                icon={Activity}
                subtext="In selected period"
            />
            <StatCard
                title="Total Volume"
                value={summary.total_volume.toLocaleString()}
                icon={Droplets}
                subtext="Gallons"
            />
            <StatCard
                title="Avg Volume"
                value={Math.round(summary.avg_volume).toLocaleString()}
                icon={AlertTriangle}
                subtext="Gallons per spill"
            />
            <StatCard
                title="Max Volume"
                value={summary.max_volume.toLocaleString()}
                icon={AlertTriangle}
                subtext="Largest single spill"
            />
        </div>
    )
}
