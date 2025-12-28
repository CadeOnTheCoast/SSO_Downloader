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
        let url =
            process?.env?.NEXT_PUBLIC_SITE_URL ?? // Set this to your site URL in production env vars
            process?.env?.NEXT_PUBLIC_VERCEL_URL ?? // Automatically set by Vercel.
            'http://localhost:3000/'
        // Make sure to include `https://` when not localhost.
        url = url.includes('http') ? url : `https://${url}`
        // Make sure to include a trailing `/`.
        url = url.charAt(url.length - 1) === '/' ? url : `${url}/`
        return url
    }

    const redirectUrl = `${getURL()}auth/callback`
    const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
            shouldCreateUser: true,
            emailRedirectTo: redirectUrl,
        },
    })

    if (error) {
        return redirect(`/login?error=${encodeURIComponent(error.message)}`)
    }

    revalidatePath('/', 'layout')
    return redirect(`/login?success=Link sent to ${email} (Redirecting to: ${redirectUrl})`)
}
