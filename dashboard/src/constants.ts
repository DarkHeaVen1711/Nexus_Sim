export interface CityOption {
  id: string;
  label: string;
}

export const CITIES: CityOption[] = [
  { id: 'chicago', label: 'Chicago' },
  { id: 'paris', label: 'Paris' },
  { id: 'ahmedabad', label: 'Ahmedabad' },
  { id: 'piedmont', label: 'Piedmont' },
];

export const GINI_THRESHOLDS = {
  LOW: 0.25,
  MODERATE: 0.45,
} as const;

export function giniLabel(g: number): string {
  if (g < GINI_THRESHOLDS.LOW) return 'Low Inequality';
  if (g < GINI_THRESHOLDS.MODERATE) return 'Moderate Inequality';
  return 'High Inequality';
}

export function giniColor(g: number): string {
  if (g < GINI_THRESHOLDS.LOW) return '#22c55e';
  if (g < GINI_THRESHOLDS.MODERATE) return '#eab308';
  return '#ef4444';
}
