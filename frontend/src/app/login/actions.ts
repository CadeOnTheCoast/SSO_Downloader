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

    const getURL = async () => {
        // 1. Try environment variables
        let url =
            process.env.NEXT_PUBLIC_SITE_URL ??
            process.env.NEXT_PUBLIC_VERCEL_URL ??
            process.env.VERCEL_URL ??
            null

        // 2. Try headers (if no env vars)
        if (!url) {
            try {
                const { headers } = await import('next/headers')
                const headersList = await headers()
                const host = headersList.get('host')
                const protocol = headersList.get('x-forwarded-proto') || 'https'
                if (host && !host.includes('localhost')) {
                    url = `${protocol}://${host}`
                }
            } catch (e) {
                // Ignore header errors
            }
        }

        // 3. Final Fallback based on environment
        if (!url) {
            if (process.env.NODE_ENV === 'production') {
                url = 'https://sso-downloader.vercel.app/'
            } else {
                url = 'http://localhost:3000/'
            }
        }

        // Normalize
        url = url.includes('http') ? url : `https://${url}`
        url = url.endsWith('/') ? url : `${url}/`
        return url
    }

    const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
            shouldCreateUser: true,
            emailRedirectTo: `${await getURL()}auth/callback`,
        },
    })

    if (error) {
        return redirect(`/login?error=${encodeURIComponent(error.message)}`)
    }

    revalidatePath('/', 'layout')
    return redirect('/login?success=Check your email for the magic link!')
}
