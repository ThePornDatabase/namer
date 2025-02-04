module.exports = {
  '*.py': (filenames) => filenames.map((filename) => `poetry run ruff check --output-format grouped "${filename}"`),
  '*.js': (filenames) => filenames.map((filename) => `pnpm eslint --no-color "${filename}"`)
}
