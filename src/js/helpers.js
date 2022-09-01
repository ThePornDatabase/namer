import $ from 'jquery'
import {Tooltip} from 'bootstrap'

export class Helpers {
    static getProgressBar() {
        return '<div class="progress"><div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div></div>'
    }

    static refreshFiles(selector, target = 'files') {
        selector.html(Helpers.getProgressBar())

        let url
        switch (target) {
            case 'queue':
                url = 'get_queued'
                break
            default:
                url = 'get_files'
        }

        Helpers.request(`./api/v1/${url}`, null, function (data) {
            Helpers.render('failedFiles', data, selector, function (selector) {
                Helpers.setTableSort(selector)
            })
        })
    }

    static setTableSort(selector) {
        $(selector).children('table').DataTable({
            stateSave: true,
            stateSaveCallback: function (settings, data) {
                localStorage.setItem('DataTables_' + settings.sInstance, JSON.stringify(data))
            },
            stateLoadCallback: function (settings) {
                return JSON.parse(localStorage.getItem('DataTables_' + settings.sInstance))
            }
        })
    }

    static render(template, res, selector, afterRender = null) {
        const data = {
            'template': template,
            'data': res,
            'url': new URL(window.document.URL).pathname
        }

        Helpers.request('./api/v1/render', data, function (data) {
            selector.html(data.response)
            afterRender?.(selector)
        })
    }

    static request(url, data, success = null) {
        const progressBar = $('#progressBar')

        $.ajax({
            xhr: function () {
                const xhr = new window.XMLHttpRequest()
                xhr.addEventListener('progress', function (evt) {
                    if (evt.lengthComputable) {
                        const percentComplete = Math.ceil(evt.loaded / evt.total * 100)
                        if (progressBar) {
                            progressBar.width(percentComplete + '%')
                        }
                    }
                }, false)

                return xhr
            },
            url: url,
            type: 'POST',
            data: JSON.stringify(data, null, 0),
            contentType: 'application/json',
            dataType: 'json',
            success: success,
        })
    }

    static initTooltips(selector) {
        const tooltips = selector.find('[data-bs-toggle="tooltip"]')
        tooltips.each(function (index, element) {
            new Tooltip(element, {
                boundary: selector[0],
            })
        })
    }
}
