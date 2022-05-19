require('bootstrap/js/dist/modal')
require('bootstrap/js/dist/tooltip')
const $ = require('jquery')

const filesResult = $('#filesResult')
const resultBody = $('#searchResults .modal-body')
const queryInput = $('#queryInput')
const deleteFile = $('#deleteFile')

const Helpers = require('./helpers')

$('.search').on('click', function () {
    resultBody.html(Helpers.getProgressBar())

    const data = {
        'query': queryInput.val(),
        'file': queryInput.data('file'),
    }

    Helpers.request('./api/v1/get_search', data, function (data) {
        Helpers.render('searchResults', data, resultBody)
    })
})

$('#refreshFiles').on('click', function () {
    filesResult.html(Helpers.getProgressBar())
    Helpers.refreshFailedFiles(filesResult)
})

filesResult.on('click', '.match', function () {
    const file = $(this).data('file')
    queryInput.val(file)
    queryInput.data('file', file)
})

$('#searchResults').on('click', '.rename', function () {
    const data = {
        'file': $(this).data('file'),
        'scene_id': $(this).data('scene-id'),
    }

    Helpers.request('./api/v1/rename', data, function () {
        Helpers.refreshFailedFiles(filesResult)
    })
})

filesResult.on('click', '.delete', function () {
    const file = $(this).data('file')
    deleteFile.val(file)
    deleteFile.data('file', file)
})

$('#deleteButton').on('click', function () {
    const data = {
        'file': deleteFile.data('file'),
    }

    Helpers.request('./api/v1/delete', data, function () {
        Helpers.refreshFailedFiles(filesResult)
    })
})
