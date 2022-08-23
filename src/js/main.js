require('bootstrap/js/dist/modal')
const hljs = require('highlight.js/lib/common')
const $ = require('jquery')
import 'datatables.net-bs5'

const filesResult = $('#filesResult')
const searchForm = $('#searchForm')
const searchButton = searchForm.find('button.search')
const resultBody = $('#searchResults .modal-body')
const logBody = $('#logFile .modal-body')
const queryInput = $('#queryInput')
const deleteFile = $('#deleteFile')
const queueSize = $('#queueSize')
const refreshFiles = $('#refreshFiles')
const searchResults = $('#searchResults')
const deleteButton = $('#deleteButton')

const Helpers = require('./helpers')

searchButton.on('click', function () {
    resultBody.html(Helpers.getProgressBar())

    const data = {
        'query': queryInput.val(),
        'file': queryInput.data('file'),
    }

    Helpers.request('./api/v1/get_search', data, function (data) {
        Helpers.render('searchResults', data, resultBody)
    })
})

queryInput.on('keyup', function (e) {
    if (e.which === 13) {
        searchButton.click()
    }
})

$('.log').on('click', function () {
    logBody.html(Helpers.getProgressBar())

    const data = {
        'file': $(this).data('file'),
    }

    Helpers.request('./api/v1/read_failed_log', data, function (data) {
        const log = hljs.highlight(data, {language: 'json'}).value
        logBody.html(`<pre><code class="hljs">${log}</pre></code>`)
    })
})

refreshFiles.on('click', function () {
    filesResult.html(Helpers.getProgressBar())
    Helpers.refreshFiles(filesResult, $(this).data('target'))
    updateQueueSize()
})

filesResult.on('click', '.match', function () {
    const query = $(this).data('query')
    const file = $(this).data('file')
    queryInput.val(query)
    queryInput.data('file', file)
})

searchForm.on('transitionend webkitTransitionEnd oTransitionEnd', function () {
    queryInput.focus()
});

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

Helpers.setTableSort(filesResult)

if (queueSize) {
    updateQueueSize()
    setInterval(function () {
        updateQueueSize()
    }, 5000)
}
