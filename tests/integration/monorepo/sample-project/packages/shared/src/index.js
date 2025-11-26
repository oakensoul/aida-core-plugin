export function formatDate(date) {
  return date.toISOString();
}

export function generateId() {
  return Math.random().toString(36).substring(7);
}
