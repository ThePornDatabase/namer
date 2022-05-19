const $ = require('jquery');

class Helpers {
    static getProgressBar() {
        return '<div class="progress"><div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div></div>'
    }

    static refreshFailedFiles(selector) {
        Helpers.request('./api/v1/get_files', null, function (data) {
            Helpers.render('failedFiles', data, selector)
        })
    }

    static render(template, res, selector) {
        const data = {
            'template': template,
            'data': res,
        }

        Helpers.request('./api/v1/render', data, function (data) {
            selector.html(data.response)
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
}

module.exports = Helpers
