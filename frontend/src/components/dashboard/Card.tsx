import React from 'react'

export function Card({ children, className = '' }: { children: React.ReactNode, className?: string }) {
    return (
        <div className={`rounded-lg border border-brand-sage/20 bg-white shadow-sm ring-1 ring-brand-sage/5 ${className}`}>
            {children}
        </div>
    )
}

export function CardHeader({ children, className = '' }: { children: React.ReactNode, className?: string }) {
    return (
        <div className={`flex flex-col space-y-1.5 p-6 ${className}`}>
            {children}
        </div>
    )
}

export function CardTitle({ children, className = '' }: { children: React.ReactNode, className?: string }) {
    return (
        <h3 className={`font-heading text-lg font-semibold leading-none tracking-tight text-brand-charcoal ${className}`}>
            {children}
        </h3>
    )
}

export function CardContent({ children, className = '' }: { children: React.ReactNode, className?: string }) {
    return (
        <div className={`p-6 pt-0 ${className}`}>
            {children}
        </div>
    )
}
