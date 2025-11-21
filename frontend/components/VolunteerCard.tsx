import { motion } from 'framer-motion'

type Props = {
  id: number
  full_name: string
  role: string
  city?: string | null
  state?: string | null
  email?: string | null
  phone?: string | null
  status: string
  availability?: string[]
}

export default function VolunteerCard({ full_name, role, city, state, email, phone, status, availability }: Props) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01 }}
      className="bg-white p-6 rounded-2xl shadow-sm hover:shadow-md transition"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold leading-tight">{full_name}</h3>
          <p className="text-sm text-slate-500">{role}</p>
        </div>
        <div className="text-right">
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${status === 'Active' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
            {status}
          </span>
        </div>
      </div>

      <div className="mt-4 text-sm text-slate-600 space-y-1">
        <div className="flex items-center gap-3">
          <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14c-4.418 0-8 1.79-8 4v1h16v-1c0-2.21-3.582-4-8-4z"/></svg>
          <span>{city || '—'}, {state || '—'}</span>
        </div>
        <div className="flex items-center gap-3">
          <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
          <span className="truncate">{email || 'No email'}</span>
        </div>
        <div className="flex items-center gap-3">
          <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2M9 21v-6M9 15h6"/></svg>
          <span>{phone || 'No phone'}</span>
        </div>
      </div>

      {availability && availability.length > 0 && (
        <div className="mt-4 text-xs text-slate-500">
          Available: {availability.join(', ')}
        </div>
      )}
    </motion.article>
  )
}
