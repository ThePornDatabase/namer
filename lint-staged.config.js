module.exports = {
  '*.py': 'poetry run flakeheaven lint --format default',
  '*.js': './node_modules/eslint/bin/eslint.js --ext .js'
}
