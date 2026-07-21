import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ADMIN_AUTH_COOKIE, ADMIN_AUTH_VALUE, getAdminPassword } from "@/lib/admin-auth";

type SearchParams = Promise<{
  error?: string;
}>;

async function authenticateAdministration(formData: FormData) {
  "use server";

  const password = String(formData.get("password") ?? "");

  if (password !== getAdminPassword()) {
    redirect("/administration?error=1");
  }

  const cookieStore = await cookies();
  cookieStore.set(ADMIN_AUTH_COOKIE, ADMIN_AUTH_VALUE, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/monitoring",
    maxAge: 60 * 60 * 8,
  });

  redirect("/monitoring");
}

export default async function AdministrationPage(props: { searchParams: SearchParams }) {
  const searchParams = await props.searchParams;
  const hasError = searchParams.error === "1";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <section className="overflow-hidden rounded-[2rem] border border-black/10 bg-white shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="flex min-h-[260px] flex-col justify-between bg-black p-8 text-white">
            <p className="w-fit rounded-full bg-white px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-black">
              Administration
            </p>
            <div>
              <h1 className="text-3xl font-black tracking-tight sm:text-4xl">Accès au monitoring</h1>
              <p className="mt-4 text-sm font-medium leading-6 text-white/70">
                Cette page donne accès aux indicateurs de moisson et à l&apos;état des connecteurs.
              </p>
            </div>
          </div>

          <div className="p-6 sm:p-8 lg:p-10">
            <h2 className="text-2xl font-black tracking-tight text-black">Connexion rapide</h2>
            <p className="mt-2 text-sm font-medium leading-6 text-slate-600">
              Saisissez le mot de passe administrateur. Il peut être modifié via la variable d&apos;environnement
              <span className="font-black text-black"> ADMIN_PASSWORD</span>, avec une valeur de secours définie dans le code.
            </p>

            <form action={authenticateAdministration} className="mt-6 space-y-4">
              <div className="space-y-2">
                <label htmlFor="password" className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">
                  Mot de passe
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  className="h-12 w-full rounded-2xl border border-black/10 bg-[#f6f3ee] px-4 text-sm font-semibold outline-none placeholder:text-slate-400 focus:border-black focus:bg-white"
                  placeholder="Mot de passe administrateur"
                />
              </div>

              {hasError ? (
                <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
                  Mot de passe incorrect. Veuillez réessayer.
                </p>
              ) : null}

              <button
                type="submit"
                className="w-full rounded-full border border-black bg-black px-5 py-3 text-sm font-black text-white shadow-sm hover:bg-white hover:text-black"
              >
                Ouvrir le monitoring
              </button>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
}
