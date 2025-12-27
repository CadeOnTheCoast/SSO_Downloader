import { formatDate } from "@/lib/utils"

interface SSOReport {
    id: string
    sso_id: string
    utility_name: string
    county: string
    volume_gallons: number | null
    date_sso_began: string | null
}

interface SSOTableProps {
    reports: SSOReport[]
}

export function SSOTable({ reports }: SSOTableProps) {
    return (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-sm">
            <div className="p-6 border-b border-slate-800">
                <h3 className="text-lg font-semibold text-white">Latest SSO Reports</h3>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-left">
                    <thead>
                        <tr className="bg-slate-800/50 text-slate-400 text-xs uppercase tracking-wider">
                            <th className="px-6 py-3 font-medium">Date</th>
                            <th className="px-6 py-3 font-medium">SSO ID</th>
                            <th className="px-6 py-3 font-medium">Utility</th>
                            <th className="px-6 py-3 font-medium">County</th>
                            <th className="px-6 py-3 font-medium text-right">Volume (Gal)</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-sm">
                        {reports.map((report) => (
                            <tr key={report.id} className="text-slate-300 hover:bg-slate-800/30 transition-colors">
                                <td className="px-6 py-4 whitespace-nowrap">
                                    {report.date_sso_began ? formatDate(report.date_sso_began) : "N/A"}
                                </td>
                                <td className="px-6 py-4 font-mono text-xs">{report.sso_id}</td>
                                <td className="px-6 py-4 max-w-[200px] truncate">{report.utility_name || "Unknown"}</td>
                                <td className="px-6 py-4">{report.county}</td>
                                <td className="px-6 py-4 text-right">
                                    {report.volume_gallons ? report.volume_gallons.toLocaleString() : "Unknown"}
                                </td>
                            </tr>
                        ))}
                        {reports.length === 0 && (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-slate-500 italic">
                                    No reports found matching the filters.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
