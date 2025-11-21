import { useEffect, useState } from 'react'
import axios from 'axios'
import { motion } from 'framer-motion'

type Volunteer = {
  id: number
  full_name: string
  role: string
  city: string | null
  state: string | null
  email: string | null
  phone: string | null
  status: string
  availability: string[]
}

export default function Home() {
  const [volunteers, setVolunteers] = useState<Volunteer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
    axios
      .get(`${base}/api/volunteers/`)
      .then((res) => {
        setVolunteers(res.data)
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-4xl font-extrabold">Volunteers</h1>
          <p className="text-slate-500 mt-2">A polished demo (Next.js + Tailwind + Framer Motion)</p>
        </header>

        {loading ? (
          <div className="p-6 bg-white rounded-lg shadow flex items-center justify-center">Loading...</div>
        ) : error ? (
          <div className="p-6 bg-rose-50 text-rose-700 rounded-lg">Error: {error}</div>
        ) : (
          <section className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {volunteers.map((v) => (
              <motion.article
                key={v.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="bg-white p-6 rounded-xl shadow hover:shadow-lg transition"
              >
                <h2 className="text-lg font-semibold">{v.full_name}</h2>
                <p className="text-sm text-slate-500">{v.role}</p>
                <div className="mt-3 text-sm text-slate-600">
                  <div>{v.city}, {v.state}</div>
                  <div>{v.email} {v.phone}</div>
                </div>
                <div className="mt-4 flex gap-2 items-center">
                  <span className={`px-2 py-1 rounded-md text-xs ${v.status === 'Active' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{v.status}</span>
                </div>
              </motion.article>
            ))}
          </section>
        )}
      </div>
    </main>
  )
}
