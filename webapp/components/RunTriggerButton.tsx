"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

type RunTriggerButtonProps = {
  label: string;
  endpoint: string;
  compact?: boolean;
};

export default function RunTriggerButton({
  label,
  endpoint,
  compact = false,
}: RunTriggerButtonProps) {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  async function handleClick() {
    setMessage(null);

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data?.error || `HTTP ${response.status}`);
      }

      setMessage("Run déclenché.");
      startTransition(() => {
        router.refresh();
      });
    } catch (error) {
      const text = error instanceof Error ? error.message : "Erreur inconnue";
      setMessage(text);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isPending}
        className={[
          "inline-flex items-center justify-center rounded-full border border-black px-4 font-black transition",
          compact ? "w-full py-2 text-xs" : "py-3 text-sm",
          isPending ? "cursor-not-allowed bg-slate-100 text-slate-400" : "bg-white text-black hover:bg-black hover:text-white",
        ].join(" ")}
      >
        {isPending ? "Envoi..." : label}
      </button>

      {message ? (
        <span className={message === "Run déclenché." ? "text-xs font-bold text-emerald-700" : "text-xs font-bold text-rose-700"}>
          {message}
        </span>
      ) : null}
    </div>
  );
}
