import { useEffect } from 'react'
import { INSTITUTION_NAME } from '../config'

/** Sets the browser tab title to the page name followed by the hospital name. */
export function usePageTitle(page?: string) {
  useEffect(() => {
    document.title = page ? `${page} | ${INSTITUTION_NAME}` : INSTITUTION_NAME
  }, [page])
}
