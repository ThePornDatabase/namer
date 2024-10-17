import $ from 'jquery'
import { Tooltip } from 'bootstrap'

export class Helpers {
  static #table
  static #queueSize = '0'

  static getProgressBar () {
    return '<div class="progress"><div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div></div>'
  }

  static refreshFiles (selector, tableButtons, target = 'files') {
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
        Helpers.setTableSort(selector, tableButtons)
      })
    })
  }

  static removeRow (selector, paging = false) {
    Helpers.#table
      .row(selector.parents('tr'))
      .remove()
      .draw(paging)
  }

  static setTableSort (selector, tableButtons) {
    Helpers.#table = $(selector).children('table').DataTable({
      stateSave: true,
      stateSaveCallback: function (settings, data) {
        localStorage.setItem('DataTables_' + settings.sInstance, JSON.stringify(data))
      },
      stateLoadCallback: function (settings) {
        return JSON.parse(localStorage.getItem('DataTables_' + settings.sInstance))
      },
      responsive: true,
      fixedHeader: true,
      colReorder: {
        fixedColumnsRight: 1
      },
      buttons: [
        {
          extend: 'colvis',
          columns: ':not(.noVis)',
          text: '<i class="bi bi-table"></i>',
          titleAttr: 'Column Visibility'
        }
      ]
    })

    tableButtons.empty()
    Helpers.#table.buttons().container().appendTo(tableButtons)
  }

  static render (template, res, selector, afterRender = null) {
    const data = {
      template,
      data: res,
      url: new URL(window.document.URL).pathname
    }

    Helpers.request('./api/v1/render', data, function (data) {
      selector.html(data.response)
      afterRender?.(selector)
    })
  }

  static request (url, data, success = null) {
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
      url,
      type: 'POST',
      data: JSON.stringify(data, null, 0),
      contentType: 'application/json',
      dataType: 'json',
      success
    })
  }

  static initTooltips (selector) {
    const tooltips = selector.find('[data-bs-toggle="tooltip"]')
    tooltips.each(function (index, element) {
      new Tooltip(element, {
        boundary: selector[0]
      })
    })
  }

  static updateQueueSize (selector) {
    Helpers.request('./api/v1/get_queue', null, function (data) {
      if (Helpers.#queueSize !== data) {
        Helpers.#queueSize = data
        selector.html(data)
      }
    })
  }
}
