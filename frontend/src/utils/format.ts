/**
 * 格式化成交额
 * @param amount 成交额（亿元）
 * @returns 格式化字符串
 */
export function formatAmount(amount: number): string {
  return `${amount.toFixed(2)}亿`;
}

/**
 * 格式化涨跌幅
 * @param pct 涨跌幅（%）
 * @returns 格式化字符串（带+/-符号）
 */
export function formatChangePct(pct: number): string {
  const abs = Math.abs(pct).toFixed(2);
  if (pct > 0) return `+${abs}%`;
  if (pct < 0) return `-${abs}%`;
  return '0.00%';
}

/**
 * 格式化市值
 * @param cap 市值（亿元）
 * @returns 格式化字符串
 */
export function formatMarketCap(cap: number): string {
  if (cap >= 10000) {
    return `${(cap / 10000).toFixed(1)}万亿`;
  }
  return `${cap.toFixed(0)}亿`;
}

/**
 * 格式化数字（加千位分隔符）
 */
export function formatNumber(num: number, decimals = 0): string {
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
