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
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <button
        type="button"
        onClick={handleClick}
        disabled={isPending}
        style={{
          appearance: "none",
          border: "1px solid #b8c4d6",
          background: isPending ? "#eef2f7" : "#ffffff",
          color: "#0a214a",
          borderRadius: 10,
          padding: compact ? "8px 12px" : "10px 14px",
          fontSize: compact ? 14 : 15,
          fontWeight: 600,
          cursor: isPending ? "not-allowed" : "pointer",
          width: compact ? "100%" : "fit-content",
        }}
      >
        {isPending ? "Envoi..." : label}
      </button>

      {message ? (
        <span
          style={{
            fontSize: 12,
            color: message === "Run déclenché." ? "#0a7d57" : "#b42318",
          }}
        >
          {message}
        </span>
      ) : null}
    </div>
  );
}
