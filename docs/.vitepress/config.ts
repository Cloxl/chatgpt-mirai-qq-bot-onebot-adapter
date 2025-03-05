// @ts-ignore
import {defineConfig} from 'vitepress'
import markdownItEmoji from 'markdown-it-emoji'
import markdownItAnchor from 'markdown-it-anchor'
import markdownItToc from 'markdown-it-toc-done-right'

export default defineConfig({
    lang: 'zh-CN',
    title: 'Onebot Adapter',
    description: 'OneBot adapter for lss233/chatgpt-mirai-qq-bot documentation - 支持NapCat和LLOneBot的QQ机器人适配器',
    // base: '/chatgpt-mirai-qq-bot-onebot-adapter/',

    vite: {
        resolve: {
            alias: {
                '@assets': '/assets'
            }
        },
        build: {
            assetsDir: 'assets',
            rollupOptions: {
                output: {
                    assetFileNames: 'assets/[name].[hash][extname]'
                }
            }
        },
    },

    lastUpdated: true,
    cleanUrls: true,
    head: [
        ['meta', { name: 'theme-color', content: '#3c8772' }],
        ['meta', { name: 'apple-mobile-web-app-capable', content: 'yes' }],
        ['meta', { name: 'apple-mobile-web-app-status-bar-style', content: 'black' }],
        ['meta', { name: 'msapplication-TileColor', content: '#3c8772' }],
        ['meta', { name: 'keywords', content: 'onebot,qq机器人,chatgpt,napcat,llonebot,kirara-ai,文档' }],
        ['meta', { name: 'author', content: 'cloxl' }],
        ['meta', { property: 'og:type', content: 'website' }],
        ['meta', { property: 'og:title', content: 'Onebot Adapter' }],
        ['meta', { property: 'og:description', content: 'OneBot adapter for lss233/chatgpt-mirai-qq-bot documentation - 支持NapCat和LLOneBot的QQ机器人适配器' }],
        ['meta', { property: 'og:url', content: 'https://github.com/Cloxl/chatgpt-mirai-qq-bot-onebot-adapter' }],
    ],
    
    themeConfig: {
        nav: [
            { text: '首页', link: '/' },
            { text: '部署指南', link: '/guide/deploy', activeMatch: '/guide/deploy' },
            { text: '配置指南', link: '/guide/plugin-config', activeMatch: '/guide/plugin-config' },
            { text: '常见问题', link: '/guide/faq', activeMatch: '/guide/faq' }
        ],
        siteTitle: 'Onebot Adapter',
        sidebar: {
            '/guide/': [
                {
                    text: '指南',
                    items: [
                        { text: '部署教程', link: '/guide/deploy' },
                        { text: '插件配置', link: '/guide/plugin-config' },
                        { text: '常见问题', link: '/guide/faq' }
                    ]
                }
            ]
        },
        editLink: {
            pattern: 'https://github.com/Cloxl/chatgpt-mirai-qq-bot-onebot-adapter/edit/docs/docs/:path',
            text: '在 GitHub 上编辑'
        },
        socialLinks: [
            {icon: 'github', link: 'https://github.com/Cloxl/chatgpt-mirai-qq-bot-onebot-adapter'}
        ],
        footer: {
            message: 'Released under the MIT License.',
            copyright: 'Copyright © 2022-present cloxl'
        },
        lastUpdated: {
            text: '最后更新于',
            formatOptions: {
                dateStyle: 'full',
                timeStyle: 'medium'
            },
        },
        outline: [1, 3],
    },
    markdown: {
        config: (md) => {
            md.use(markdownItEmoji)
            md.use(markdownItAnchor, {
                permalinkSymbol: '#',
                permalinkBefore: true,
                permalinkClass: 'anchor',
                permalinkSpace: true,
                level: [1, 2, 3],
                slugify: (s) => s.toLowerCase().replace(/[\s\(\)]/g, '-')
            })
            md.use(markdownItToc, {
                level: [2, 3],
                containerClass: 'table-of-contents'
            })
        }
    },
    sitemap: {
        hostname: 'https://github.com/Cloxl/chatgpt-mirai-qq-bot-onebot-adapter',
        lastmodDateOnly: false
    }
})

