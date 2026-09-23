import { defineConfig } from 'vitepress'

// GitHub Pages serves a project site from /<repo>/, so the base has to match
// the repo name. Set DOCS_BASE=/ when serving from a custom domain or a user
// site, otherwise every asset 404s and the page loads unstyled.
//
// The dev server is the exception and must run at '/'. With a non-root base,
// Vite prefixes its own node_modules imports with it and then cannot resolve
// them, so `vitepress dev` dies on:
//
//   Failed to resolve import ".../theme-default/styles/fonts.css"
//
// The production build is unaffected, which is what makes it confusing: the
// site builds and deploys fine while the dev server refuses to start.
const isDev = process.argv.includes('dev')
const base = process.env.DOCS_BASE ?? (isDev ? '/' : '/game-asset-engine/')

export default defineConfig({
  title: 'Game Asset Engine',
  description:
    'Turn a written description into a textured, rigged, animated game asset on your own machine.',
  base,
  lang: 'en-GB',
  cleanUrls: true,
  lastUpdated: true,
  head: [['link', { rel: 'icon', href: `${base}favicon.svg` }]],

  // Localhost URLs are instructions, not links. The checker cannot reach a
  // server that only exists on the reader's own machine.
  ignoreDeadLinks: [/^https?:\/\/localhost/, /^https?:\/\/127\.0\.0\.1/],

  themeConfig: {
    logo: '/logo.svg',

    search: {
      provider: 'local',
      options: {
        detailedView: true,
      },
    },

    nav: [
      { text: 'Guide', link: '/guide/', activeMatch: '/guide/' },
      { text: 'Reference', link: '/reference/workflows', activeMatch: '/reference/' },
      { text: 'Credits', link: '/credits' },
      {
        text: 'Repo',
        link: 'https://github.com/Xander-Rudolph/game-asset-engine',
      },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting started',
          items: [
            { text: 'What this is', link: '/guide/' },
            { text: 'Install and first run', link: '/guide/install' },
            { text: 'Running the published image', link: '/guide/running-the-image' },
            { text: 'Installing it for Claude', link: '/guide/claude' },
            { text: 'The MCP server', link: '/guide/mcp' },
            { text: 'Make your first asset', link: '/guide/first-asset' },
          ],
        },
        {
          text: 'Making things',
          items: [
            { text: 'Concept art', link: '/guide/concept-art' },
            { text: 'Turning art into a mesh', link: '/guide/meshes' },
            { text: 'TRELLIS', link: '/guide/trellis' },
            { text: 'Textures', link: '/guide/textures' },
            { text: 'Ground and terrain', link: '/guide/terrain' },
            {
              text: 'Ground relief and blending',
              link: '/guide/ground-and-relief',
            },
            { text: 'Icons', link: '/guide/icons' },
            { text: 'Props and scenery', link: '/guide/props' },
            { text: 'Music', link: '/guide/music' },
          ],
        },
        {
          text: 'Making things move',
          items: [
            { text: 'Face counts and decimation', link: '/guide/decimation' },
            { text: 'Rigging', link: '/guide/rigging' },
            { text: 'Animation cycles', link: '/guide/animation' },
            { text: 'Facings and camera angles', link: '/guide/facings' },
            { text: 'Two render engines', link: '/guide/render-engines' },
            { text: 'Talking portraits', link: '/guide/talking-portraits' },
            { text: 'Daz figures', link: '/guide/daz-figures' },
          ],
        },
        {
          text: 'Keeping it tidy',
          items: [
            { text: 'Curating and cleanup', link: '/guide/cleanup' },
            { text: 'Licensing', link: '/guide/licensing' },
            { text: 'Redistributing the image', link: '/guide/redistributing' },
            { text: 'When something breaks', link: '/guide/troubleshooting' },
          ],
        },
      ],
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'Workflows', link: '/reference/workflows' },
            { text: 'Scripts', link: '/reference/scripts' },
            { text: 'Skills and MCP', link: '/reference/skills' },
            { text: 'Credits', link: '/credits' },
            { text: 'Models and weights', link: '/reference/models' },
            { text: 'Docker and versions', link: '/reference/docker' },
            { text: 'Closing the loop', link: '/reference/closing-the-loop' },
          ],
        },
        {
          text: 'Research',
          items: [
            { text: 'Source Filmmaker', link: '/reference/source-filmmaker' },
            { text: 'Lip sync and talking portraits', link: '/reference/lip-sync' },
            { text: 'DAZ Genesis', link: '/reference/daz-genesis' },
            { text: 'Hair cards', link: '/reference/hair-cards' },
            { text: 'Commercial character tools', link: '/reference/character-tools' },
            { text: 'Character asset costs', link: '/reference/character-assets' },
            { text: 'Virt-A-Mate assets', link: '/reference/vam-assets' },
          ],
        },
      ],
    },

    outline: { level: [2, 3], label: 'On this page' },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Xander-Rudolph/game-asset-engine' },
    ],

    footer: {
      message:
        'Model weights carry their own licences. See the licensing guide before shipping anything.',
      copyright: 'Xanderu',
    },

    editLink: {
      pattern:
        'https://github.com/Xander-Rudolph/game-asset-engine/edit/main/docs/:path',
      text: 'Suggest a change to this page',
    },
  },
})
