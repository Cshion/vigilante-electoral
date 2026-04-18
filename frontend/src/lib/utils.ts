/**
 * Format actas percentage with minimum 3 decimals.
 * If the number has more than 3 decimals, show all of them.
 * 
 * @example
 * formatActas(93.4)      => "93.400"
 * formatActas(93.41567)  => "93.41567"
 * formatActas(0)         => "0.000"
 */
export function formatActas(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '0.000';
  }
  
  const str = value.toString();
  const decimals = str.includes('.') ? str.split('.')[1].length : 0;
  return decimals < 3 ? value.toFixed(3) : str;
}
