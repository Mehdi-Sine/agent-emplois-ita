import Image from "next/image";
import Link from "next/link";

const navigation = [
  { href: "/", label: "Jobs" },
  { href: "/archives", label: "Archives" },
  { href: "/typologie", label: "Typologie" },
  { href: "/monitoring", label: "Monitoring" },
  { href: "/mentions-legales", label: "Mentions légales" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-black/10 bg-[#f6f3ee]/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <Link href="/" className="flex min-w-0 items-center gap-3" aria-label="Retour à l'accueil Acta Jobs">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-black/10 bg-white shadow-sm">
            <Image
              src="/acta-logo.jpg"
              alt="Logo Acta"
              width={42}
              height={42}
              className="h-9 w-9 object-contain"
              priority
            />
          </span>
          <span className="min-w-0">
            <span className="block text-lg font-black tracking-tight text-black sm:text-xl">Acta Jobs</span>
            <span className="block truncate text-xs font-medium text-slate-600 sm:text-sm">
              Les offres des instituts techniques agricoles
            </span>
          </span>
        </Link>

        <nav className="flex items-center gap-2 overflow-x-auto pb-1 text-sm font-bold text-slate-800 lg:pb-0">
          {navigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="whitespace-nowrap rounded-full border border-black/10 bg-white px-4 py-2 shadow-sm hover:border-black hover:bg-black hover:text-white"
            >
              {item.label}
            </Link>
          ))}
          <a
            href="https://www.acta.asso.fr/"
            target="_blank"
            rel="noreferrer"
            className="whitespace-nowrap rounded-full border border-black bg-black px-4 py-2 text-white shadow-sm hover:bg-white hover:text-black"
          >
            acta.asso.fr
          </a>
        </nav>
      </div>
    </header>
  );
}
