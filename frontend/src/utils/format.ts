/**
 * Türkçe sayı/yüzde formatlama yardımcıları.
 * Ondalık ayırıcı virgül (,), binlik ayırıcı nokta (.) — tr-TR standardı.
 */

/** Yüzde değerini Türkçe formatında döndürür: 47.6 → "47,6" */
export function formatPercent(value: number, decimals = 1): string {
  return value.toFixed(decimals).replace('.', ',')
}

/** Para/sayı değerini tr-TR locale ile formatlar: 1234567 → "1.234.567" */
export function formatNumber(value: number, decimals = 0): string {
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/** Milyonluk kısaltma — Türkçe "Mn" kullanır: 1234567 → "1,23 Mn" */
export function formatMillion(value: number, decimals = 2): string {
  return (value / 1_000_000).toFixed(decimals).replace('.', ',') + ' Mn'
}

/** ECharts / Recharts eksen formatter — büyük sayıları kısaltır */
export function axisFormatter(value: number): string {
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(1).replace('.', ',') + ' Mn'
  if (value >= 1_000) return (value / 1_000).toFixed(0) + ' B'
  return value.toLocaleString('tr-TR')
}
