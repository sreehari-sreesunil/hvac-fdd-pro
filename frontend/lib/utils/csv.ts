// Hand-rolled parser, not a library: this app's CSV needs are limited to
// well-structured, comma-delimited exports (data loggers, BMS dumps), so a
// small state machine covering basic quoted fields is enough.

export type ParsedCsv = {
  headers: string[];
  rows: string[][];
};

const LONG_FORMAT_REQUIRED_COLUMNS = ["asset_id", "external_key", "value", "recorded_at"];

function parseCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (inQuotes) {
      if (char === '"') {
        if (line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        current += char;
      }
    } else if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current.trim());
  return cells;
}

export function parseCsv(text: string): ParsedCsv {
  const lines = text.split(/\r\n|\n|\r/).filter((line) => line.length > 0);
  if (lines.length === 0) return { headers: [], rows: [] };
  return {
    headers: parseCsvLine(lines[0]),
    rows: lines.slice(1).map(parseCsvLine),
  };
}

/** True if the header row already matches the /telemetry/csv-upload contract. */
export function isLongFormatHeader(headers: string[]): boolean {
  const normalized = new Set(headers.map((h) => h.trim().toLowerCase()));
  return LONG_FORMAT_REQUIRED_COLUMNS.every((col) => normalized.has(col));
}

/** Best-effort guess at which wide-format column holds the timestamp. */
export function guessTimestampColumn(headers: string[]): string | null {
  const pattern = /date|time|timestamp|recorded_at/i;
  return headers.find((h) => pattern.test(h)) ?? null;
}

/**
 * Reformats a timestamp cell to ISO-8601 UTC ("...Z"), matching the
 * convention used elsewhere in this system (see ingest_test_data.py) of
 * treating a naive wall-clock timestamp as already-correct and simply
 * appending "Z" — deliberately NOT round-tripped through a JS Date object
 * for reformatting, since that would reinterpret it in the browser's local
 * timezone and silently shift every reading.
 */
export function toIsoUtc(raw: string): string | null {
  const trimmed = raw.trim();

  const dateOnly = trimmed.match(/^\d{4}-\d{2}-\d{2}$/);
  if (dateOnly) return `${trimmed}T00:00:00Z`;

  const match = trimmed.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z)?$/);
  if (!match) return null;

  const [, datePart, timePart] = match;
  const iso = `${datePart}T${timePart}Z`;
  return Number.isNaN(Date.parse(iso)) ? null : iso;
}

export type WideReading = {
  asset_id: string;
  external_key: string;
  value: number;
  recorded_at: string;
};

export type SkippedCell = {
  row: number;
  column: string;
  reason: string;
};

/**
 * Pivots a wide-format sheet (one row per timestamp, one column per sensor)
 * into the flat {asset_id, external_key, value, recorded_at} shape the
 * backend expects. A blank cell means "no reading for this sensor at this
 * timestamp" and is skipped silently; a non-blank cell that isn't a valid
 * number is skipped and reported, mirroring the CSV-upload endpoint's
 * "partial success is normal" behavior on the client side.
 */
export function pivotWideCsv(
  parsed: ParsedCsv,
  timestampColumnIndex: number,
  assetId: string,
): { readings: WideReading[]; skipped: SkippedCell[] } {
  const readings: WideReading[] = [];
  const skipped: SkippedCell[] = [];
  const timestampHeader = parsed.headers[timestampColumnIndex];

  parsed.rows.forEach((row, i) => {
    const rowNumber = i + 2; // row 1 is the header, matching the CSV-upload endpoint's convention

    const rawTimestamp = row[timestampColumnIndex] ?? "";
    const isoTimestamp = toIsoUtc(rawTimestamp);
    if (!isoTimestamp) {
      skipped.push({
        row: rowNumber,
        column: timestampHeader,
        reason: `Invalid timestamp: "${rawTimestamp}"`,
      });
      return;
    }

    parsed.headers.forEach((header, colIndex) => {
      if (colIndex === timestampColumnIndex) return;

      const raw = (row[colIndex] ?? "").trim();
      if (raw === "") return;

      const value = Number(raw);
      if (Number.isNaN(value)) {
        skipped.push({ row: rowNumber, column: header, reason: `Not a number: "${raw}"` });
        return;
      }

      readings.push({ asset_id: assetId, external_key: header, value, recorded_at: isoTimestamp });
    });
  });

  return { readings, skipped };
}

export function chunkArray<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < items.length; i += size) chunks.push(items.slice(i, i + size));
  return chunks;
}
