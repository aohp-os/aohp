import WebSocket from "ws";
import { randomUUID } from "crypto";
import type { JsonRpcRequest, JsonRpcResponse } from "./schema";

export async function rpc(
  url: string,
  method: string,
  params: Record<string, unknown> = {},
  timeoutMs = 120_000,
): Promise<JsonRpcResponse> {
  const id = randomUUID();
  const req: JsonRpcRequest = { id, method, params };

  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    const t = setTimeout(() => {
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      reject(new Error(`timeout after ${timeoutMs}ms`));
    }, timeoutMs);

    ws.on("open", () => {
      ws.send(JSON.stringify(req));
    });

    ws.on("message", (data) => {
      clearTimeout(t);
      try {
        const text = data.toString();
        const res = JSON.parse(text) as JsonRpcResponse;
        ws.close();
        resolve(res);
      } catch (e) {
        ws.close();
        reject(e);
      }
    });

    ws.on("error", (err: Error & { code?: string }) => {
      clearTimeout(t);
      const code = err.code ?? "";
      if (code === "ECONNREFUSED" || code === "ECONNRESET") {
        err.message +=
          ` (${url} — start AOHP AgentDriver and ensure its WebSocket service is running on this device)`;
      }
      reject(err);
    });
  });
}
