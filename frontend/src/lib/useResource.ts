import { api } from "@/api";
import { useCallback, useEffect, useState } from "react";
export function useResource<T>(
  path: string,
  initial: T,
  refreshKey: unknown = 0,
  interval = 5000,
) {
  const [data, setData] = useState(initial);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      setData(await api<T>(path));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [path]);
  useEffect(() => {
    void load();
    const id = setInterval(load, interval);
    return () => clearInterval(id);
  }, [load, refreshKey, interval]);
  return { data, error, load };
}
