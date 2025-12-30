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
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 flex flex-col items-center text-center group hover:border-blue-500/30 transition-all">
                    <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <Activity className="h-6 w-6 text-blue-500" />
                    </div>
                    <div className="text-4xl font-bold text-white mb-2">{summary.total_count.toLocaleString()}</div>
                    <div className="text-sm font-medium text-slate-400 uppercase tracking-wider">Raw sewage spills</div>
                    <div className="mt-4 pt-4 border-t border-slate-800 w-full text-xs text-slate-500">
                        Avg <span className="text-slate-300 font-semibold">{spillsPerDay}</span>/day since {formatDate(startDate)}
                    </div>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 flex flex-col items-center text-center group hover:border-emerald-500/30 transition-all">
                    <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <Droplets className="h-6 w-6 text-emerald-500" />
                    </div>
                    <div className="text-4xl font-bold text-white mb-2">{summary.total_volume.toLocaleString()}</div>
                    <div className="text-sm font-medium text-slate-400 uppercase tracking-wider">Gallons of raw sewage</div>
                    <div className="mt-4 pt-4 border-t border-slate-800 w-full text-xs text-slate-500">
                        Avg <span className="text-slate-300 font-semibold">{gallonsPerHour}</span> gal/hour
                    </div>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 flex flex-col items-center text-center group hover:border-amber-500/30 transition-all">
                    <div className="h-12 w-12 rounded-full bg-amber-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <AlertTriangle className="h-6 w-6 text-amber-500" />
                    </div>
                    <div className="text-4xl font-bold text-white mb-2 text-wrap px-4">{durationStr}</div>
                    <div className="text-sm font-medium text-slate-400 uppercase tracking-wider">Total spill duration</div>
                    <div className="mt-4 pt-4 border-t border-slate-800 w-full text-xs text-slate-500 italic">
                        Cumulative time spilling raw sewage
                    </div>
                </div>
            </div>

            {/* Fun Analogies Section */}
            {summary.volume_analogies && summary.volume_analogies.length > 0 && (
                <div className="bg-gradient-to-br from-blue-900/10 to-transparent border border-blue-500/10 rounded-xl p-8">
                    <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-[0.2em] mb-6 text-center">Volume Perspective</h3>

                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                        {summary.volume_analogies.map((analogy, idx) => (
                            <div key={idx} className="bg-slate-950/40 border border-slate-800 rounded-lg p-5 relative overflow-hidden group hover:border-blue-500/20 transition-all">
                                <div className="absolute -top-1 -right-1 text-3xl opacity-[0.03] group-hover:opacity-[0.08] transition-opacity">
                                    {analogy.emoji}
                                </div>
                                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                                    <span>{analogy.emoji}</span> {analogy.label}
                                </div>
                                <div className="text-xl font-bold text-white mb-1">{analogy.value}</div>
                                <div className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                                    {analogy.text}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
