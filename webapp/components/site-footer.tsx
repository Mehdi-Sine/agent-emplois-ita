import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-10 border-t border-black/10 bg-black text-white">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[1.3fr_0.7fr] lg:px-8">
        <div>
          <p className="text-lg font-black tracking-tight">Acta Jobs</p>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-white/70">
            Agrégateur expérimental des offres d&apos;emploi et de stage publiées par les instituts techniques agricoles.
            Les informations sont collectées automatiquement et doivent être vérifiées sur les sites sources.
          </p>
        </div>

        <div className="flex flex-col gap-2 text-sm font-semibold sm:flex-row sm:flex-wrap lg:justify-end">
          <Link href="/mentions-legales" className="rounded-full bg-white/10 px-4 py-2 hover:bg-white hover:text-black">
            Mentions légales
          </Link>
          <a
            href="https://www.acta.asso.fr/"
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-white/10 px-4 py-2 hover:bg-white hover:text-black"
          >
            Site de l&apos;Acta
          </a>
        </div>
      </div>
    </footer>
  );
}
