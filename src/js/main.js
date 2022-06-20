require('bootstrap/js/dist/modal')
const $ = require('jquery')

const filesResult = $('#filesResult')
const resultBody = $('#searchResults .modal-body')
const logBody = $('#logFile .modal-body')
const queryInput = $('#queryInput')
const deleteFile = $('#deleteFile')
const queueSize = $('#queueSize')
const refreshFiles = $('#refreshFiles')
const searchResults = $('#searchResults')
const deleteButton = $('#deleteButton')

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

$('.log').on('click', function () {
    logBody.html(Helpers.getProgressBar())

    const data = {
        'file': $(this).data('file'),
    }

    Helpers.request('./api/v1/read_failed_log', data, function (data) {
        Helpers.render('logFile', data, logBody)
    })
})

refreshFiles.on('click', function () {
    filesResult.html(Helpers.getProgressBar())
    Helpers.refreshFiles(filesResult, $(this).data('target'))
    updateQueueSize()
})

filesResult.on('click', '.match', function () {
    const file = $(this).data('file')
    queryInput.val(file)
    queryInput.data('file', file)
})

searchResults.on('click', '.rename', function () {
    const data = {
        'file': $(this).data('file'),
        'scene_id': $(this).data('scene-id'),
    }

    Helpers.request('./api/v1/rename', data, function () {
        Helpers.refreshFiles(filesResult)
    })
})

filesResult.on('click', '.delete', function () {
    const file = $(this).data('file')
    deleteFile.val(file)
    deleteFile.data('file', file)
})

deleteButton.on('click', function () {
    const data = {
        'file': deleteFile.data('file'),
    }

    Helpers.request('./api/v1/delete', data, function () {
        Helpers.refreshFiles(filesResult)
    })
})

function updateQueueSize() {
    Helpers.request('./api/v1/get_queue', null, function (data) {
        Helpers.render('queueSize', data, queueSize)
    })
}

if (queueSize) {
    updateQueueSize()
    setInterval(function () {
        updateQueueSize()
    }, 5000)
}
