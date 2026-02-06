/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Discord-inspired colors
        discord: {
          bg: {
            primary: '#1e1f22',
            secondary: '#2b2d31',
            tertiary: '#313338',
          },
          blurple: '#5865f2',
          blurpleHover: '#4752c4',
          green: '#23a559',
          red: '#da373c',
          yellow: '#f0b232',
          text: {
            primary: '#f2f3f5',
            secondary: '#b5bac1',
            muted: '#949ba4',
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
