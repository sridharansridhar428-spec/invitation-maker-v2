/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",   // Flask Jinja templates
    "./static/**/*.js"         // Any frontend JS files
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
