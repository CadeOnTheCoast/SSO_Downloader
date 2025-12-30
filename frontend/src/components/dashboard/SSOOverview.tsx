'use client'

import React from 'react'
import { Droplets, Activity, Building2, MapPin, AlertTriangle } from 'lucide-react'
import { Card } from './Card'
import { DashboardSummary } from '@/lib/api'

function formatHumanDuration(totalHours: number): string {
    const days_total = Math.floor(totalHours / 24);
    const hours = Math.round(totalHours % 24);
    const years = Math.floor(days_total / 365);
    const remaining_days_total = days_total % 365;
    const weeks = Math.floor(remaining_days_total / 7);
    const days = remaining_days_total % 7;

    const parts = [];
    if (years > 0) parts.push(`${years} year${years > 1 ? 's' : ''}`);
    if (weeks > 0) parts.push(`${weeks} week${weeks > 1 ? 's' : ''}`);
    if (days > 0) parts.push(`${days} day${days > 1 ? 's' : ''}`);
    if (hours > 0) parts.push(`${hours} hour${hours > 1 ? 's' : ''}`);

    return parts.length > 0 ? parts.join(', ') : '0 hours';
}

function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString();
}

interface SSOOverviewProps {
    summary: DashboardSummary | null;
}

export function SSOOverview({ summary }: SSOOverviewProps) {
    if (!summary) return null;

    const startDate = summary.date_range?.min;
    const endDate = summary.date_range?.max;

    let days = 1;
    if (startDate && endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        days = Math.max(1, Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1);
    }

    const spillsPerDay = (summary.total_count / days).toFixed(1);
    const totalHours = days * 24;
    const gallonsPerHour = (summary.total_volume / totalHours).toLocaleString(undefined, { maximumFractionDigits: 1 });
    const durationStr = formatHumanDuration(summary.total_duration_hours ?? 0);

    return (
        <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between pb-2">
                        <h3 className="text-sm font-medium text-slate-400">Raw sewage spills</h3>
                        <Activity className="h-4 w-4 text-blue-500" />
                    </div>
                    <p className="text-slate-300 text-sm leading-relaxed">
                        There were <span className="text-white font-bold">{summary.total_count}</span> raw sewage spills from {formatDate(startDate)} to {formatDate(endDate)}. That's about <span className="text-white font-bold">{spillsPerDay}</span> spills per day.
                    </p>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between pb-2">
                        <h3 className="text-sm font-medium text-slate-400">Gallons of raw sewage</h3>
                        <Droplets className="h-4 w-4 text-emerald-500" />
                    </div>
                    <p className="text-slate-300 text-sm leading-relaxed">
                        From {formatDate(startDate)} to {formatDate(endDate)}, <span className="text-white font-bold">{(summary.total_volume ?? 0).toLocaleString()}</span> gallons of raw sewage were reported. That's about <span className="text-white font-bold">{gallonsPerHour}</span> gallons spilled per hour.
                    </p>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between pb-2">
                        <h3 className="text-sm font-medium text-slate-400">Time sewage was spilling</h3>
                        <AlertTriangle className="h-4 w-4 text-amber-500" />
                    </div>
                    <p className="text-slate-300 text-sm leading-relaxed">
                        Raw sewage was spilling for about <span className="text-white font-bold">{durationStr}</span> over this period.
                    </p>
                </div>
            </div>

            {/* Fun Analogies Section */}
            {summary.volume_analogies && summary.volume_analogies.length > 0 && (
                <div className="bg-gradient-to-br from-blue-900/20 to-slate-900 border border-blue-500/20 rounded-xl p-8">
                    <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                        <Activity className="h-5 w-5 text-blue-400" />
                        How much is that?
                    </h3>

                    <p className="text-slate-300 leading-relaxed mb-6">
                        Approximately <span className="text-white font-bold">{(summary.total_volume ?? 0).toLocaleString()}</span> gallons of raw sewage were reported over this period.
                        {summary.volume_analogies.map(a => a.text).join(' ')}
                    </p>

                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                        {summary.volume_analogies.map((analogy, idx) => (
                            <div key={idx} className="bg-slate-950/50 border border-blue-500/10 rounded-lg p-4 relative overflow-hidden group hover:border-blue-500/30 transition-colors">
                                <div className="absolute top-2 right-2 text-2xl opacity-10 group-hover:opacity-20 transition-opacity">
                                    {analogy.emoji}
                                </div>
                                <div className="text-xs font-medium text-blue-400 mb-1">{analogy.label}</div>
                                <div className="text-xl font-bold text-white">{analogy.value}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
