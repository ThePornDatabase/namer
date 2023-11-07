module.exports = {
  '*.py': (filenames) => filenames.map((filename) => `poetry run ruff check --output-format text "${filename}"`),
  '*.js': (filenames) => filenames.map((filename) => `pnpm eslint --no-color "${filename}"`)
}
