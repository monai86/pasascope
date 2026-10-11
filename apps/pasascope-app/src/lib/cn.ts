type ClassPart = string | false | null | undefined;

/** Joins class names, dropping the falsy parts of conditional expressions. */
export function cn(...parts: ClassPart[]): string {
  return parts.filter(Boolean).join(" ");
}
