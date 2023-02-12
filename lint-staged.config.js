module.exports = {
  '*.py': (filenames) => filenames.map((filename) => `poetry run flakeheaven lint --format default "${filename}"`),
  '*.js': (filenames) => filenames.map((filename) => `pnpm eslint --no-color "${filename}"`)
}
