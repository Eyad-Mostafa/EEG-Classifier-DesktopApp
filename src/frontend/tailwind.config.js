/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: 'class', // Important for the .dark class in css
  theme: {
    extend: {
      colors: {
        // These keys map to your CSS variables
        primary: 'var(--primary)',
        'primary-hover': 'var(--primary-hover)',
        accent: 'var(--accent)',

        // Backgrounds
        bg: {
          main: 'var(--bg-main)',
          card: 'var(--bg-card)',
          hover: 'var(--bg-hover)',
        },

        // Text
        text: {
          main: 'var(--text-main)',
          muted: 'var(--text-muted)',
          inverted: 'var(--text-inverted)',
        },

        // Borders
        'border-color': 'var(--border-color)',
      }
    },
  },
  plugins: [],
}