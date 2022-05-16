'use strict'

const path = require('path')

const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin')
const TerserPlugin = require('terser-webpack-plugin')

const targetPath = path.resolve(__dirname, 'namer', 'web', 'public', 'assets')
const target = 'chrome 75'

module.exports = {
    entry: [
        './src/js/main.js',
        './src/css/main.scss'
    ],
    mode: 'production',
    output: {
        path: targetPath,
        filename: 'bundle.min.js'
    },
    plugins: [
        new MiniCssExtractPlugin({
            filename: 'bundle.min.css'
        })
    ],
    module: {
        rules: [
            {
                test: /\.s[ac]ss$/i,
                use: [
                    MiniCssExtractPlugin.loader,
                    'css-loader',
                    'sass-loader'
                ]
            },
            {
                test: /\.js$/i,
                exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: [
                            ['@babel/preset-env', {targets: target}]
                        ]
                    }
                }
            }
        ]
    },
    optimization: {
        minimizer: [
            new CssMinimizerPlugin({
                minimizerOptions: {
                    preset: [
                        'default',
                        {
                            discardComments: {
                                removeAll: true
                            }
                        }
                    ]
                }
            }),
            new TerserPlugin({
                extractComments: false,
                terserOptions: {
                    format: {
                        comments: false,
                    },
                },
            })
        ]
    }
}

