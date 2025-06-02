/**
 * SECURITY NOTE: Frontend validation removed for security reasons.
 * The frontend should never know the secret prime number.
 * All real validation happens on the backend.
 */

const PRO_KEY_STORAGE_KEY = 'ii_agent_pro_key';

/**
 * Saves a Pro key to local storage
 * @param proKey The Pro key to save
 */
export function saveProKeyToStorage(proKey: string): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem(PRO_KEY_STORAGE_KEY, proKey);
  } catch (error) {
    console.warn('Failed to save Pro key to localStorage:', error);
  }
}

/**
 * Gets the Pro key from local storage
 * @returns The Pro key if present, null otherwise
 */
export function getProKeyFromStorage(): string | null {
  if (typeof window === 'undefined') return null;
  
  try {
    return localStorage.getItem(PRO_KEY_STORAGE_KEY);
  } catch (error) {
    console.warn('Failed to get Pro key from localStorage:', error);
    return null;
  }
}

/**
 * Removes the Pro key from local storage
 */
export function removeProKeyFromStorage(): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.removeItem(PRO_KEY_STORAGE_KEY);
  } catch (error) {
    console.warn('Failed to remove Pro key from localStorage:', error);
  }
}

/**
 * Checks if user has Pro access based on URL parameters OR local storage
 * Note: This is just for UI purposes. Real validation happens on the backend.
 * @returns boolean indicating if user appears to have Pro access
 */
export function hasProAccess(): boolean {
  if (typeof window === 'undefined') return false;
  
  // First check URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  const proUserKeyFromUrl = urlParams.get('pro_user_key');
  
  // If we have a key in URL, save it to storage and use it
  if (proUserKeyFromUrl && isValidProKeyFormat(proUserKeyFromUrl)) {
    saveProKeyToStorage(proUserKeyFromUrl);
    return true;
  }
  
  // If no URL key, check local storage
  const proUserKeyFromStorage = getProKeyFromStorage();
  if (proUserKeyFromStorage && isValidProKeyFormat(proUserKeyFromStorage)) {
    return true;
  }
  
  return false;
}

/**
 * Gets the Pro key from URL parameters OR local storage
 * Priority: URL parameter > Local storage
 * @returns The Pro key if present, null otherwise
 */
export function getProKey(): string | null {
  if (typeof window === 'undefined') return null;
  
  // First check URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  const proUserKeyFromUrl = urlParams.get('pro_user_key');
  
  if (proUserKeyFromUrl && isValidProKeyFormat(proUserKeyFromUrl)) {
    // Save to storage for future use
    saveProKeyToStorage(proUserKeyFromUrl);
    return proUserKeyFromUrl;
  }
  
  // If no URL key, check local storage
  const proUserKeyFromStorage = getProKeyFromStorage();
  if (proUserKeyFromStorage && isValidProKeyFormat(proUserKeyFromStorage)) {
    return proUserKeyFromStorage;
  }
  
  return null;
}

/**
 * Gets the Pro key from URL parameters only (legacy function)
 * @returns The Pro key if present, null otherwise
 */
export function getProKeyFromUrl(): string | null {
  if (typeof window === 'undefined') return null;
  
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('pro_user_key');
}

/**
 * Validates the format of a Pro key (8 characters, hex format)
 * @param proKey The Pro key to validate
 * @returns boolean indicating if the format is valid
 */
function isValidProKeyFormat(proKey: string): boolean {
  if (!proKey) return false;
  
  // Basic format validation only (8 characters, hex format)
  const hexPattern = /^[0-9A-Fa-f]{8}$/;
  return hexPattern.test(proKey);
} 