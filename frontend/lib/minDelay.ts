/**
 * Ensures a promise takes at least `ms` milliseconds to resolve.
 * Prevents loading spinners from flashing on fast responses.
 */
export function minDelay<T>(promise: Promise<T>, ms = 400): Promise<T> {
  const delay = new Promise<void>((resolve) => setTimeout(resolve, ms));
  return Promise.all([promise, delay]).then(([result]) => result);
}
