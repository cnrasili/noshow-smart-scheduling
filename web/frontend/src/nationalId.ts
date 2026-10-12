// Turkish national ID number (T.C. kimlik numarası) check, same rules as the web backend

export function isValidNationalId(value: string): boolean {
  if (!/^[1-9][0-9]{10}$/.test(value)) return false
  const d = [...value].map(Number)
  const odd = d[0] + d[2] + d[4] + d[6] + d[8]
  const even = d[1] + d[3] + d[5] + d[7]
  const tenth = (((odd * 7 - even) % 10) + 10) % 10
  const eleventh = d.slice(0, 10).reduce((sum, digit) => sum + digit, 0) % 10
  return d[9] === tenth && d[10] === eleventh
}
