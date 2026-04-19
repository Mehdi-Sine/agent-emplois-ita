type DispatchOptions = {
  source?: string | null;
};

function getRequiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing environment variable: ${name}`);
  }
  return value;
}

export async function dispatchCollectWorkflow(options: DispatchOptions = {}) {
  const token = getRequiredEnv("GITHUB_TOKEN");
  const owner = getRequiredEnv("GITHUB_OWNER");
  const repo = getRequiredEnv("GITHUB_REPO");
  const workflow = process.env.GITHUB_WORKFLOW_FILE || "manual-collect.yml";
  const ref = process.env.GITHUB_REF || "main";

  const payload: Record<string, unknown> = { ref };

  if (options.source) {
    payload.inputs = {
      source: options.source,
    };
  }

  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "ITA-Jobs-Webapp",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`GitHub workflow dispatch failed (${response.status}): ${text}`);
  }

  return {
    ok: true,
    workflow,
    ref,
    source: options.source ?? null,
  };
}
