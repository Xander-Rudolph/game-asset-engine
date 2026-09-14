// The default VitePress theme with this site's own styling on top. Everything
// visual lives in custom.css, so upgrading VitePress does not mean re-reading
// this file.
import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import './custom.css'

export default DefaultTheme satisfies Theme
