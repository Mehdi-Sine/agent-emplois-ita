import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div>
          <Link href="/" className="text-xl font-semibold tracking-tight text-slate-900">
            ITA Jobs
          </Link>
          <p className="mt-1 text-sm text-slate-600">
            Offres d&apos;emploi et de stage des instituts techniques agricoles.
          </p>
        </div>
        <nav className="flex flex-wrap items-center gap-3 text-sm font-medium text-slate-700">
          <Link href="/" className="rounded-full px-3 py-2 hover:bg-slate-100">
            Offres actives
          </Link>
          <Link href="/archives" className="rounded-full px-3 py-2 hover:bg-slate-100">
            Archives
          </Link>
          <Link href="/monitoring" className="rounded-full px-3 py-2 hover:bg-slate-100">
            Monitoring
          </Link>
        </nav>
      </div>
    </header>
  );
}
