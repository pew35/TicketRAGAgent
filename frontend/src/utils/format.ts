// Formatting helpers for dates, message previews, and UI labels.
export function shortText(value: string, maxLength = 80) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 3)}...` : value;
}
