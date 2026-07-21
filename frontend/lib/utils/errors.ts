export type ApiErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "unavailable"
  | "validation"
  | "unknown";

export class ApiError extends Error {
  status: number;
  kind: ApiErrorKind;
  fieldErrors?: Record<string, string>;

  constructor(
    status: number,
    kind: ApiErrorKind,
    message: string,
    fieldErrors?: Record<string, string>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.kind = kind;
    this.fieldErrors = fieldErrors;
  }
}

function kindForStatus(status: number): ApiErrorKind {
  switch (status) {
    case 401:
      return "unauthorized";
    case 403:
      return "forbidden";
    case 404:
      return "not_found";
    case 503:
      return "unavailable";
    case 422:
      return "validation";
    default:
      return "unknown";
  }
}

type FastApiValidationError = { loc: (string | number)[]; msg: string; type: string };

/** Normalizes both FastAPI error shapes ({detail: string} and 422's {detail: [...]})
 *  into a single typed ApiError. */
export async function normalizeErrorResponse(response: Response): Promise<ApiError> {
  const status = response.status;
  const kind = kindForStatus(status);

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // no JSON body
  }

  const detail = (body as { detail?: unknown } | null)?.detail;

  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    for (const err of detail as FastApiValidationError[]) {
      const field = err.loc?.[err.loc.length - 1];
      if (field != null) fieldErrors[String(field)] = err.msg;
    }
    const message = detail[0]?.msg ?? "Check the highlighted fields.";
    return new ApiError(status, "validation", message, fieldErrors);
  }

  if (typeof detail === "string") {
    return new ApiError(status, kind, detail);
  }

  return new ApiError(status, kind, `Request failed with status ${status}.`);
}
