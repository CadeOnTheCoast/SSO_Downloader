export interface DashboardSummary {
    total_count: number
    total_volume: number
    avg_volume: number
    max_volume: number
    total_duration_hours?: number
    distinct_utilities?: number
    distinct_receiving_waters?: number
    date_range?: { min: string | null; max: string | null }
    top_utilities_pie?: any[]
    by_receiving_water?: {
        name: string
        total_volume: number
        spills: number
    }[]
    volume_analogies?: {
        label: string
        value: string
        emoji: string
        text: string
    }[]
    time_series?: SeriesPoint[]
    by_utility?: any[]
}

export interface SeriesPoint {
    date: string
    count: number
    volume: number
    [key: string]: any;
}

export interface BarGroup {
    label: string
    count: number
    total_volume_gallons: number
    [key: string]: any;
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
    utilities: {
        id: string;
        name: string;
        slug: string;
        permits: string[];
        aliases: string[];
    }[]
    counties: string[]
}

export interface FilterState {
    utility_id?: string
    utility_ids?: string[]
    utility_name?: string
    permit?: string
    permits?: string[]
    county?: string
    start_date?: string
    end_date?: string
    limit?: number
    offset?: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
}

function buildParams(filters: FilterState): URLSearchParams {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
        if (value === undefined || value === null) return
        if (Array.isArray(value)) {
            value.forEach(v => params.append(key, v))
        } else {
            params.append(key, String(value))
        }
    })
    return params
}

export async function fetchFilters(): Promise<FilterOptions> {
    const res = await fetch('/filters')
    if (!res.ok) throw new Error('Failed to fetch filters')
    return res.json()
}

export async function fetchSummary(filters: FilterState): Promise<DashboardSummary> {
    const params = buildParams(filters)
    const res = await fetch(`/summary?${params.toString()}`)
    if (!res.ok) throw new Error('Failed to fetch summary')
    return res.json()
}

export async function fetchSeriesByDate(filters: FilterState): Promise<{ points: SeriesPoint[] }> {
    const params = buildParams(filters)
    const res = await fetch(`/series/by_date?${params.toString()}`)
    if (!res.ok) throw new Error('Failed to fetch series by date')
    return res.json()
}

export async function fetchSeriesByUtility(filters: FilterState): Promise<{ bars: BarGroup[] }> {
    const params = buildParams(filters)
    const res = await fetch(`/series/by_utility?${params.toString()}`)
    if (!res.ok) throw new Error('Failed to fetch series by utility')
    return res.json()
}

export async function fetchRecords(
    filters: FilterState,
    offset: number = 0,
    limit: number = 50,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc'
): Promise<{ records: SSORecord[], total: number }> {
    const params = buildParams({
        ...filters,
        offset,
        limit,
        sort_by: sortBy,
        sort_order: sortOrder
    })
    const res = await fetch(`/records?${params.toString()}`)
    if (!res.ok) throw new Error('Failed to fetch records')
    return res.json()
}
