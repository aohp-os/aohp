export type JsonRpcRequest = {
  id: string;
  method: string;
  params?: Record<string, unknown>;
};

export type JsonRpcResponse = {
  id: string;
  ok: boolean;
  result?: unknown;
  error?: { code: string; message: string };
};
