import {Popover, Tooltip, Modal} from 'bootstrap'

const $ = require('jquery')
import 'datatables.net-bs5'

const filesResult = $('#filesResult')
const resultForm = $('#searchResults .modal-body')
const logForm = $('#logFile .modal-body')
const searchForm = $('#searchForm')
const searchButton = $('#searchForm .modal-footer .search')
const queryInput = $('#queryInput')
const deleteFile = $('#deleteFile')
const queueSize = $('#queueSize')
const refreshFiles = $('#refreshFiles')
const deleteButton = $('#deleteButton')

const Helpers = require('./helpers')

searchButton.on('click', function () {
    resultForm.html(Helpers.getProgressBar())

    const data = {
        'query': queryInput.val(),
        'file': queryInput.data('file'),
    }

    Helpers.request('./api/v1/get_search', data, function (data) {
        Helpers.render('searchResults', data, resultForm)
    })
})

queryInput.on('keyup', function (e) {
    if (e.which === 13) {
        searchButton.click()
    }
})

filesResult.on('click', '.match', function () {
    const query = $(this).data('query')
    const file = $(this).data('file')
    queryInput.val(query)
    queryInput.data('file', file)
})

filesResult.on('click', '.log', function () {
    logForm.html(Helpers.getProgressBar())

    const data = {
        'file': $(this).data('file'),
    }

    Helpers.request('./api/v1/read_failed_log', data, function (data) {
        Helpers.render('logFile', data, logForm, function (selector) {
            const tooltips = selector.find('[data-bs-toggle="tooltip"]')
            tooltips.each(function (index, element) {
                new Tooltip(element, {
                    boundary: selector,
                })
            })
        })
    })
})

filesResult.on('click', '.delete', function () {
    const file = $(this).data('file')
    deleteFile.val(file)
    deleteFile.data('file', file)
})

refreshFiles.on('click', function () {
    filesResult.html(Helpers.getProgressBar())
    Helpers.refreshFiles(filesResult, $(this).data('target'))
    updateQueueSize()
})

searchForm.on('transitionend webkitTransitionEnd oTransitionEnd', function () {
    queryInput.focus()
})

resultForm.on('click', '.rename', rename)
logForm.on('click', '.rename', rename)

deleteButton.on('click', function () {
    const data = {
        'file': deleteFile.data('file'),
    }

    Helpers.request('./api/v1/delete', data, function () {
        Helpers.refreshFiles(filesResult)
    })
})

function rename() {
    const data = {
        'file': $(this).data('file'),
        'scene_id': $(this).data('scene-id'),
    }

    Helpers.request('./api/v1/rename', data, function () {
        Helpers.refreshFiles(filesResult)
    })
}

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
