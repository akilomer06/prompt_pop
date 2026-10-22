export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    headers:
      options.body instanceof FormData
        ? options.headers
        : { "Content-Type": "application/json", ...options.headers },
    credentials: "same-origin",
  });
  if (!response.ok) {
    let message = "The request could not be completed. Try again.";
    try {
      const r = await response.json();
      message =
        typeof r.detail === "string"
          ? r.detail
          : "Check the entered values and try again.";
    } catch {}
    throw new ApiError(response.status, message);
  }
  return response.json();
}
export const send = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});
export function upload<T>(
  path: string,
  data: FormData,
  progress: (n: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api" + path);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) progress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) resolve(data);
        else
          reject(
            new Error(
              typeof data.detail === "string"
                ? data.detail
                : "Check your submission and try again.",
            ),
          );
      } catch {
        reject(
          new Error(
            "Unexpected server response. Retry with the same submission.",
          ),
        );
      }
    };
    xhr.onerror = () =>
      reject(
        new Error(
          "Connection lost. Your work is kept here. Retry to confirm acceptance.",
        ),
      );
    xhr.send(data);
  });
}
