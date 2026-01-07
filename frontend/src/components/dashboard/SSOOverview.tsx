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
        <div className="space-y-4 md:space-y-6">
            <div className="grid gap-4 grid-cols-1 md:grid-cols-3">
                <div className="bg-white border border-brand-sage/20 rounded-lg p-6 md:p-8 flex flex-col items-center text-center shadow-sm group hover:border-brand-teal transition-all">
                    <div className="h-10 w-10 md:h-12 md:w-12 rounded-full bg-brand-teal/10 flex items-center justify-center mb-3 md:mb-4 group-hover:scale-110 transition-transform">
                        <Activity className="h-5 w-5 md:h-6 md:w-6 text-brand-teal" />
                    </div>
                    <div className="text-4xl md:text-5xl font-heading font-bold text-brand-charcoal mb-2">{summary.total_count.toLocaleString()}</div>
                    <div className="text-[10px] md:text-xs font-bold text-brand-charcoal/40 uppercase tracking-[0.2em]">Raw sewage spills</div>
                    <div className="mt-3 md:mt-4 pt-3 md:pt-4 border-t border-brand-sage/10 w-full text-[10px] md:text-xs text-brand-charcoal/60">
                        Avg <span className="text-brand-charcoal font-bold">{spillsPerDay}</span>/day since {formatDate(startDate)}
                    </div>
                </div>

                <div className="bg-white border border-brand-terracotta/20 rounded-lg p-6 md:p-8 flex flex-col items-center text-center shadow-sm group hover:border-brand-terracotta transition-all">
                    <div className="h-10 w-10 md:h-12 md:w-12 rounded-full bg-brand-terracotta/10 flex items-center justify-center mb-3 md:mb-4 group-hover:scale-110 transition-transform">
                        <Droplets className="h-5 w-5 md:h-6 md:w-6 text-brand-terracotta" />
                    </div>
                    <div className="text-4xl md:text-5xl font-heading font-bold text-brand-charcoal mb-2">{summary.total_volume.toLocaleString()}</div>
                    <div className="text-[10px] md:text-xs font-bold text-brand-charcoal/40 uppercase tracking-[0.2em]">Gallons of raw sewage</div>
                    <div className="mt-3 md:mt-4 pt-3 md:pt-4 border-t border-brand-terracotta/10 w-full text-[10px] md:text-xs text-brand-charcoal/60">
                        Avg <span className="text-brand-terracotta font-bold">{gallonsPerHour}</span> gal/hour
                    </div>
                </div>

                <div className="bg-white border border-brand-sage/20 rounded-lg p-6 md:p-8 flex flex-col items-center text-center shadow-sm group hover:border-brand-mint transition-all">
                    <div className="h-10 w-10 md:h-12 md:w-12 rounded-full bg-brand-mint/10 flex items-center justify-center mb-3 md:mb-4 group-hover:scale-110 transition-transform">
                        <AlertTriangle className="h-5 w-5 md:h-6 md:w-6 text-brand-charcoal" />
                    </div>
                    <div className="text-2xl md:text-3xl font-heading font-bold text-brand-charcoal mb-2 text-wrap px-4">{durationStr}</div>
                    <div className="text-[10px] md:text-xs font-bold text-brand-charcoal/40 uppercase tracking-[0.2em]">Total spill duration</div>
                    <div className="mt-3 md:mt-4 pt-3 md:pt-4 border-t border-brand-sage/10 w-full text-[10px] md:text-xs text-brand-charcoal/40 italic">
                        Cumulative time spilling raw sewage
                    </div>
                </div>
            </div>

            {/* Fun Analogies Section */}
            {summary.volume_analogies && summary.volume_analogies.length > 0 && (
                <div className="bg-brand-sage/5 border border-brand-sage/20 rounded-lg p-6 md:p-8">
                    <h3 className="text-[10px] md:text-xs font-bold text-brand-charcoal uppercase tracking-[0.3em] mb-6 md:mb-8 text-center">Volume Perspective</h3>

                    <div className="grid gap-4 md:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
                        {summary.volume_analogies.map((analogy, idx) => (
                            <div key={idx} className="bg-white border border-brand-sage/10 rounded-lg p-4 md:p-6 relative overflow-hidden group hover:border-brand-teal/30 transition-all shadow-sm">
                                <div className="absolute -top-2 -right-2 text-4xl opacity-[0.05] group-hover:opacity-[0.1] transition-opacity">
                                    {analogy.emoji}
                                </div>
                                <div className="text-[10px] font-bold text-brand-charcoal/40 uppercase tracking-widest mb-2 md:mb-3 flex items-center gap-2">
                                    <span>{analogy.emoji}</span> {analogy.label}
                                </div>
                                <div className="text-xl md:text-2xl font-heading font-bold text-brand-charcoal mb-2">{analogy.value}</div>
                                <div className="text-xs text-brand-charcoal/70 line-clamp-2 italic leading-relaxed">
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
