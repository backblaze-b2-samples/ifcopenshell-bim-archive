"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api-client";

/**
 * A copyable snippet showing how a downstream viewer / coordination tool pulls
 * a short-lived presigned URL for any archived object — no B2 keys leave the
 * server. This is how the archive serves models + geometry back out.
 */
export function DownstreamSnippet({ slug }: { slug: string }) {
  const [copied, setCopied] = useState(false);

  const snippet = `# Ask the API to presign any object under this project's B2 prefix.
# The response is a short-lived GET URL — feed it straight to an IFC/OBJ viewer.
curl "${API_BASE}/projects/${slug}/artifacts/download?key=projects/${slug}/geometry/<model>.obj.zip"
# -> { "url": "https://s3.<region>.backblazeb2.com/...&X-Amz-Signature=..." }`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — the snippet is still selectable */
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between border-b border-border py-4 px-5">
        <CardTitle className="card-title">Serve to downstream tools</CardTitle>
        <Button variant="outline" size="sm" onClick={copy} className="h-7">
          {copied ? (
            <Check className="h-3.5 w-3.5" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
          {copied ? "Copied" : "Copy"}
        </Button>
      </CardHeader>
      <CardContent className="p-5">
        <pre className="overflow-x-auto rounded-md border border-border bg-muted/40 p-3 text-xs">
          <code>{snippet}</code>
        </pre>
      </CardContent>
    </Card>
  );
}
