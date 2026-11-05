// Qatar is UTC+3 all year (no daylight saving).
export function qatarHour(now = new Date()): number {
  return Number(new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Qatar', hour: 'numeric', hourCycle: 'h23' }).format(now))
}
