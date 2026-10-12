import { INSTITUTION_NAME } from '../config'

/** The hospital's own mark: a rounded square with a plus sign; made for this project. */
export function Logo() {
  return (
    <svg className="logo" viewBox="0 0 40 40" role="img" aria-labelledby="logo-title">
      <title id="logo-title">{`${INSTITUTION_NAME} logosu`}</title>
      <rect width="40" height="40" rx="9" className="logo-tile" />
      <path d="M16 9h8v7h7v8h-7v7h-8v-7H9v-8h7z" className="logo-mark" />
    </svg>
  )
}
