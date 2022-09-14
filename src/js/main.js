import {Popover, Modal} from 'bootstrap'
import $ from 'jquery'
import 'datatables.net-bs5'
import {escape} from 'lodash'
import hljs from 'highlight.js'

import {Helpers} from './helpers'

const filesResult = $('#filesResult')
const resultForm = $('#searchResults .modal-body')
const resultFormTitle = $('#modalSearchResultsLabel span')
const logForm = $('#logFile .modal-body')
const logFormTitle = $('#modalLogsLabel span')
const searchForm = $('#searchForm')
const searchButton = $('#searchForm .modal-footer .search')
const queryInput = $('#queryInput')
const deleteFile = $('#deleteFile')
const queueSize = $('#queueSize')
const refreshFiles = $('#refreshFiles')
const deleteButton = $('#deleteButton')

searchButton.on('click', function () {
    resultForm.html(Helpers.getProgressBar())

    const data = {
        'query': queryInput.val(),
        'file': queryInput.data('file'),
    }

    const title = escape(`(${data['file']}) [${data['query']}]`)
    resultFormTitle.html(title)
    resultFormTitle.attr('title', title)

    Helpers.request('./api/v1/get_search', data, function (data) {
        Helpers.render('searchResults', data, resultForm, function (selector) {
            Helpers.initTooltips(selector)
        })
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

    const title = escape(`[${data['file']}]`)

    logFormTitle.html(title)
    logFormTitle.attr('title', title)

    Helpers.request('./api/v1/read_failed_log', data, function (data) {
        Helpers.render('logFile', data, logForm, function (selector) {
            Helpers.initTooltips(selector)
        })
    })
})

filesResult.on('click', '.delete', function () {
    const file = $(this).data('file')
    deleteFile.val(file)
    deleteFile.data('file', file)
})

refreshFiles.on('click', function () {
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
        queueSize.html(data)
    })
}

Helpers.setTableSort(filesResult)
hljs.highlightAll()

if (queueSize) {
    updateQueueSize()
    setInterval(function () {
        updateQueueSize()
    }, 5000)
}
