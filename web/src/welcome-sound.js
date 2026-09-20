/** Play welcome clip after login/register; failures are silent. */
export function playWelcomeSound() {
  try {
    const a = new Audio(`${import.meta.env.BASE_URL}welcome.mp3`);
    a.play().catch(() => {});
  } catch {
    /* ignore */
  }
}
