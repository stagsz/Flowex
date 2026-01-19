import { createClient, SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY
const devAuthBypass = import.meta.env.VITE_DEV_AUTH_BYPASS === 'true'

// Create a mock client for dev bypass mode to avoid OAuth calls
const createMockClient = (): SupabaseClient => {
  const mockAuth = {
    getSession: async () => ({ data: { session: null }, error: null }),
    signInWithOAuth: async () => ({ data: { provider: '', url: '' }, error: null }),
    signOut: async () => ({ error: null }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
  }
  return { auth: mockAuth } as unknown as SupabaseClient
}

let supabase: SupabaseClient

if (devAuthBypass) {
  console.info('Dev auth bypass enabled - using mock Supabase client')
  supabase = createMockClient()
} else if (!supabaseUrl || !supabaseAnonKey) {
  console.warn('Supabase credentials not configured. Using mock client.')
  supabase = createMockClient()
} else {
  supabase = createClient(supabaseUrl, supabaseAnonKey)
}

export { supabase }
