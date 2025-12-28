'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'

export async function login(formData: FormData) {
    const supabase = await createClient()
    const email = formData.get('email') as string

    if (!email) {
        return redirect('/login?error=Email is required')
    }

    // Pre-validate domain (safety check before sending email)
    const allowedDomains = (process.env.ALLOWED_DOMAINS || 'mobilebaykeeper.org')
        .split(',')
        .map(d => d.trim().replace(/^@/, '').toLowerCase())
    const userDomain = email.split('@')[1]?.toLowerCase()

    if (!userDomain || !allowedDomains.includes(userDomain)) {
        return redirect('/login?error=Only authorized domains are allowed')
    }

    const getURL = () => {
        // Try environment variables first
        let url =
            process.env.NEXT_PUBLIC_SITE_URL ??
            process.env.NEXT_PUBLIC_VERCEL_URL ??
            process.env.VERCEL_URL ??
            null

        // If no env vars, try to get from headers (more reliable in server actions)
        if (!url) {
            const { headers } = require('next/headers')
            const headersList = headers()
            const host = headersList.get('host')
            const protocol = headersList.get('x-forwarded-proto') || 'https'
            if (host) {
                url = `${protocol}://${host}`
            }
        }

        // Final fallback
        if (!url) {
            url = 'http://localhost:3000/'
        }

        // Make sure to include `https://` when not localhost.
        url = url.includes('http') ? url : `https://${url}`
        // Make sure to include a trailing `/`.
        url = url.endsWith('/') ? url : `${url}/`
        return url
    }

    const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
            shouldCreateUser: true,
            emailRedirectTo: `${getURL()}auth/callback`,
        },
    })

    if (error) {
        return redirect(`/login?error=${encodeURIComponent(error.message)}`)
    }

    revalidatePath('/', 'layout')
    return redirect('/login?success=Check your email for the magic link!')
}
