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

    // Pre-validate domain or email (safety check before sending email)
    const allowedDomains = (process.env.ALLOWED_DOMAINS || 'mobilebaykeeper.org')
        .split(',')
        .map(d => d.trim().replace(/^@/, '').toLowerCase())
    const allowedEmails = (process.env.ALLOWED_EMAILS || '')
        .split(',')
        .map(e => e.trim().replace(/['"]+/g, '').toLowerCase())
        .filter(e => e !== '')

    // Fallback hardcoded allowed emails
    const hardcodedAllowedEmails = ['mfearn2307@gmail.com']
    allowedEmails.push(...hardcodedAllowedEmails)

    const userDomain = email.split('@')[1]?.toLowerCase()
    const lowerEmail = email.toLowerCase()

    const isAllowedDomain = userDomain && allowedDomains.includes(userDomain)
    const isAllowedEmail = allowedEmails.includes(lowerEmail)

    if (!isAllowedDomain && !isAllowedEmail) {
        return redirect('/login?error=This email or domain is not authorized')
    }

    const getURL = async () => {
        // FORCE PRODUCTION URL
        // We are temporarily removing all logic to ensure Vercel uses this URL.
        return 'https://sso-downloader.vercel.app/'
    }

    const redirectUrl = `${await getURL()}auth/callback`
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
    return redirect('/login?success=Check your email for the magic link!')
}
