/*globals $*/
$(function() {
    const filesResult = $('#filesResult');
    const resultBody = $('#searchResults .modal-body');
    const queryInput = $('#queryInput');

    $('.search').on('click', function() {
        resultBody.html(getProgressBar());

        const data = {
            'query': queryInput.val(),
            'file': queryInput.data('file'),
        }

        request('./get_search', data, function(data) {
            render('searchResults', data, resultBody);
        })
    });

    filesResult.on('click', '.match', function() {
        const file = $(this).data('file')
        queryInput.val(file);
        queryInput.data('file', file);
    });

    $('#refreshFiles').on('click', function() {
        refreshFiles();
    });

    $('#searchResults').on('click', '.rename', function() {
        const data = {
            'file': $(this).data('file'),
            'scene_id': $(this).data('scene-id'),
        }

        request('./rename', data, function() {
            refreshFiles();
        })
    });

    function render(template, res, selector) {
        const data = {
            'template': template,
            'data': res,
        }

        request('./render', data, function(data) {
            selector.html(data.response);
        })
    }

    function getProgressBar() {
        return '<div class="progress"><div id="searchResultsProgress" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div></div>';
    }

    function refreshFiles() {
        request('./get_files', null, function(data) {
            render('failedFiles', data, filesResult);
        });
    }

    function request(url, data, success = null) {
        const searchResultsProgress = $('#searchResultsProgress');

        $.ajax({
            xhr: function() {
                const xhr = new window.XMLHttpRequest();
                xhr.addEventListener('progress', function(evt) {
                    if (evt.lengthComputable) {
                        const percentComplete = Math.ceil(evt.loaded / evt.total * 100);
                        if (searchResultsProgress) {
                            searchResultsProgress.width(percentComplete + '%');
                        }
                    }
                }, false);

                return xhr;
            },
            url: url,
            type: 'POST',
            data: JSON.stringify(data, null, 0),
            contentType: 'application/json',
            dataType: 'json',
            success: success,
        });
    }
});
