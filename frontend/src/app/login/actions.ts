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
        // FORCE PRODUCTION URL
        // We are temporarily removing all logic to ensure Vercel uses this URL.
        return 'https://sso-downloader.vercel.app/'
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
