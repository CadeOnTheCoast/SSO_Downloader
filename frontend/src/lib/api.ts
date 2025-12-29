export interface DashboardSummary {
    total_count: number
    total_volume: number
    avg_volume: number
    max_volume: number
    top_utilities_pie?: any[]
}

export interface SeriesPoint {
    date: string
    count: number
    volume: number
}

export interface BarGroup {
    label: string
    count: number
    total_volume_gallons: number
}

export interface SSORecord {
    id: string
    utility_name: string
    county: string
    date_sso_began: string
    volume_gallons: number
    cause: string
    receiving_water: string
    address: string
}

export interface FilterOptions {
    utilities: { id: string; name: string }[]
    counties: string[]
}

export interface FilterState {
    utility_id?: string
    county?: string
    start_date?: string
    end_date?: string
    limit?: number
}

export async function fetchFilters(): Promise<FilterOptions> {
    const res = await fetch('/filters')
    if (!res.ok) throw new Error('Failed to fetch filters')
    return res.json()
}

export async function fetchSummary(filters: FilterState): Promise<DashboardSummary> {
    const params = new URLSearchParams(filters as any)
    const res = await fetch(`/summary?${params.toString()}`)
    if (!res.ok) throw new Error('Failed to fetch summary')
    return res.json()
}

export async function fetchSeriesByDate(filters: FilterState): Promise<{ points: SeriesPoint[] }> {
    const params = new URLSearchParams(filters as any)
    const res = await fetch(`/series/by_date?${params.toString()}`)
    if (!res.ok) throw new Error('Failed to fetch series by date')
    return res.json()
}

export async function fetchSeriesByUtility(filters: FilterState): Promise<{ bars: BarGroup[] }> {
    const params = new URLSearchParams(filters as any)
    const res = await fetch(`/series/by_utility?${params.toString()}`)
    if (!res.ok) throw new Error('Failed to fetch series by utility')
    return res.json()
}

export async function fetchRecords(filters: FilterState, offset: number = 0, limit: number = 50): Promise<{ records: SSORecord[], total: number }> {
    const params = new URLSearchParams({ ...filters, offset: offset.toString(), limit: limit.toString() } as any)
    const res = await fetch(`/records?${params.toString()}`)
    if (!res.ok) throw new Error('Failed to fetch records')
    return res.json()
}
