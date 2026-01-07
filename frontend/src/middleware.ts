import { type NextRequest } from 'next/server'
import { updateSession } from '@/lib/supabase/middleware'

export async function middleware(request: NextRequest) {
    const userAgent = request.headers.get('user-agent') || ''
    const isMobile = /mobile/i.test(userAgent)
    const response = await updateSession(request)
    response.headers.set('x-is-mobile', isMobile ? 'true' : 'false')
    return response
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * Feel free to modify this pattern to include more paths.
         */
        '/((?!_next/static|_next/image|favicon.ico|auth|login|api|summary|series|records|filters|download|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
    ],
}
