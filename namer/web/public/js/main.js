/*globals $*/
$(function () {
    const resultBody = $('#searchResults .modal-body');
    const queryInput = $('#queryInput');
    const searchResultsProgress = $('#searchResultsProgress');

    $('.search').on('click', function () {
        resultBody.html('<div class="progress"><div id="searchResultsProgress" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div></div>');

        const data = {
            'query': queryInput.val(),
            'file': queryInput.data('file'),
        }
        $.ajax({
            xhr: function () {
                const xhr = new window.XMLHttpRequest();
                xhr.addEventListener("progress", function (evt) {
                    if (evt.lengthComputable) {
                        const percentComplete = Math.ceil(evt.loaded / evt.total * 100);
                        searchResultsProgress.width(percentComplete + '%');
                    }
                }, false);

                return xhr;
            },
            url: "/get_search",
            type: "POST",
            data: JSON.stringify(data, null, 4),
            contentType: 'application/json',
            dataType: 'json',
            success: function (data) {
                data = getSearchResultHTML(data);
                resultBody.html(data);
            }
        });
    });

    $('.match').on('click', function () {
        const file = $(this).data('file')
        queryInput.val(file);
        queryInput.data('file', file);
    });

    $('#searchResults').on('click', '.rename', function () {
        const data = {
            'file': $(this).data('file'),
            'scene_id': $(this).data('scene-id'),
        }

        $.ajax({
            url: "/rename",
            type: "POST",
            data: JSON.stringify(data, null, 4),
            contentType: 'application/json',
            dataType: 'json',
        });
    });

    function getSearchResultHTML(data) {
        let html = '<div class="row row-cols-auto">';

        data.files.forEach(function (value) {
            html += '<div class="col m-1">';
            html += '<div class="card h-100" style="width:12rem">';
            html += `<img class="card-img-top" src="${value.poster}" alt="${value.title}">`
            html += '<div class="card-body">';
            html += `<h5 class="card-title">${value.title}</h5>`
            html += `<p class="card-text">${value.date}</p>`
            html += '</div>'
            html += `<div class="card-footer">`
            html += `<a href="https://metadataapi.net/scenes/${value.id}" class="btn btn-secondary">Show</a>`
            html += `<button class="btn btn-primary float-end rename" data-bs-dismiss="modal" data-scene-id="${value.id}" data-file="${data.file}">Select</button>`
            html += '</div>'
            html += '</div>'
            html += '</div>'
        })

        html += '</div>'

        return html;
    }
});