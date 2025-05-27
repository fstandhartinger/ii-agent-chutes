// Prime number for Pro key validation (large prime in the hundreds of thousands range)
const PRO_PRIME = 982451; // A large prime number

/**
 * Validates if a Pro key is valid based on the prime number logic
 * @param proKey - The hex string to validate
 * @returns boolean indicating if the key is valid
 */
export function validateProKey(proKey: string): boolean {
  try {
    // Convert hex to decimal
    const decimalValue = parseInt(proKey, 16);
    
    // Check if it's a valid number and a multiple of our prime
    if (isNaN(decimalValue) || decimalValue <= 0) {
      return false;
    }
    
    return decimalValue % PRO_PRIME === 0;
  } catch {
    return false;
  }
}

/**
 * Generates a new valid Pro key
 * @returns A hex string that is a valid Pro key
 */
export function generateProKey(): string {
  // Generate a random multiplier (1-1000)
  const multiplier = Math.floor(Math.random() * 1000) + 1;
  
  // Calculate the decimal value
  const decimalValue = PRO_PRIME * multiplier;
  
  // Convert to hex and ensure it's 8 characters
  const hexValue = decimalValue.toString(16).toUpperCase();
  
  // Pad with zeros if necessary to make it 8 characters
  return hexValue.padStart(8, '0');
}

/**
 * Checks if user has Pro access based on URL parameters
 * @returns boolean indicating if user has Pro access
 */
export function hasProAccess(): boolean {
  if (typeof window === 'undefined') return false;
  
  const urlParams = new URLSearchParams(window.location.search);
  const proUserKey = urlParams.get('pro_user_key');
  
  if (!proUserKey) return false;
  
  return validateProKey(proUserKey);
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