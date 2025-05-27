/**
 * SECURITY NOTE: Frontend validation removed for security reasons.
 * The frontend should never know the secret prime number.
 * All real validation happens on the backend.
 */

/**
 * Checks if user has Pro access based on URL parameters
 * Note: This is just for UI purposes. Real validation happens on the backend.
 * @returns boolean indicating if user appears to have Pro access
 */
export function hasProAccess(): boolean {
  if (typeof window === 'undefined') return false;
  
  const urlParams = new URLSearchParams(window.location.search);
  const proUserKey = urlParams.get('pro_user_key');
  
  // Simple check: if there's a pro_user_key parameter that looks like a hex string
  if (!proUserKey) return false;
  
  // Basic format validation only (8 characters, hex format)
  const hexPattern = /^[0-9A-Fa-f]{8}$/;
  return hexPattern.test(proUserKey);
}

/**
 * Gets the Pro key from URL parameters
 * @returns The Pro key if present, null otherwise
 */
export function getProKeyFromUrl(): string | null {
  if (typeof window === 'undefined') return null;
  
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('pro_user_key');
} 