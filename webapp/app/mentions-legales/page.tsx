export default function LegalPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <section className="rounded-[2rem] border border-black/10 bg-white p-6 shadow-sm sm:p-8">
        <p className="inline-flex rounded-full bg-black px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-white">
          Informations
        </p>
        <h1 className="mt-5 text-3xl font-black tracking-tight text-black sm:text-5xl">Mentions légales</h1>
        <p className="mt-4 text-base font-medium leading-8 text-slate-700">
          Acta Jobs est un service expérimental d&apos;agrégation d&apos;offres d&apos;emploi et de stage publiées par
          les instituts techniques agricoles. Le site est mis à jour automatiquement par un agent informatique
          utilisant des traitements automatisés et de l&apos;intelligence artificielle. Malgré les contrôles mis en place,
          il peut contenir des erreurs, des doublons, des annonces expirées ou des informations incomplètes.
        </p>
      </section>

      <section className="rounded-[2rem] border border-black/10 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-xl font-black tracking-tight text-black">Responsabilité et vérification</h2>
        <p className="mt-4 text-sm font-medium leading-7 text-slate-700">
          Les informations présentées sur Acta Jobs sont fournies à titre indicatif. Avant toute candidature,
          l&apos;utilisateur doit vérifier les informations sur le site source de l&apos;institut concerné. Les liens vers les
          annonces d&apos;origine sont proposés pour faciliter cette vérification.
        </p>
      </section>

      <section className="rounded-[2rem] border border-black/10 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-xl font-black tracking-tight text-black">Liens utiles</h2>
        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
          <a
            href="https://www.acta.asso.fr/"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-full bg-black px-5 py-3 text-sm font-black text-white hover:bg-slate-800"
          >
            Site officiel de l&apos;Acta ↗
          </a>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-full border border-black px-5 py-3 text-sm font-black text-black hover:bg-black hover:text-white"
          >
            Retour aux offres
          </a>
        </div>
      </section>
    </div>
  );
}
