Vue.component(VueQrcode.name, VueQrcode)

var maplnurldevice = obj => {
  obj._data = _.clone(obj)
  obj.theTime = obj.time * 60 - (Date.now() / 1000 - obj.timestamp)
  obj.time = obj.time + 'mins'

  if (obj.time_elapsed) {
    obj.date = 'Time elapsed'
  } else {
    obj.date = Quasar.utils.date.formatDate(
      new Date((obj.theTime - 3600) * 1000),
      'HH:mm:ss'
    )
  }
  return obj
}
var mapatmpayments = obj => {
  obj._data = _.clone(obj)
  obj.time = obj.timestamp * 60 - (Date.now() / 1000 - obj.timestamp)
  return obj
}

new Vue({
  el: '#vue',
  mixins: [windowMixin],
  data: function () {
    return {
      tab: 'mails',
      protocol: window.location.protocol,
      location: window.location.hostname,
      wslocation: window.location.hostname,
      filter: '',
      currency: 'USD',
      lnurlValue: '',
      websocketMessage: '',
      lnurldeviceLinks: [],
      atmLinks: [],
      lnurldeviceLinksObj: [],
      boltzToggleState: false,
      devices: [
        {
          label: 'PoS',
          value: 'pos'
        },
        {
          label: 'ATM',
          value: 'atm'
        },
        {
          label: 'Switch',
          value: 'switch'
        }
      ],
      lnurldevicesTable: {
        columns: [
          {
            name: 'title',
            align: 'left',
            label: 'title',
            field: 'title'
          },
          {
            name: 'theId',
            align: 'left',
            label: 'id',
            field: 'id'
          },
          {
            name: 'key',
            align: 'left',
            label: 'key',
            field: 'key'
          },
          {
            name: 'wallet',
            align: 'left',
            label: 'wallet',
            field: 'wallet'
          },
          {
            name: 'device',
            align: 'left',
            label: 'device',
            field: 'device'
          },
          {
            name: 'currency',
            align: 'left',
            label: 'currency',
            field: 'currency'
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      atmTable: {
        columns: [
          {
            name: 'id',
            align: 'left',
            label: 'ID',
            field: 'id'
          },
          {
            name: 'deviceid',
            align: 'left',
            label: 'Device ID',
            field: 'deviceid'
          },
          {
            name: 'sats',
            align: 'left',
            label: 'Sats',
            field: 'sats'
          },
          {
            name: 'time',
            align: 'left',
            label: 'Date',
            field: 'time'
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      passedlnurldevice: {},
      settingsDialog: {
        show: false,
        data: {}
      },
      formDialog: {
        show: false,
        data: {}
      },
      formDialoglnurldevice: {
        show: false,
        data: {
          extra: [],
          lnurl_toggle: false,
          show_message: false,
          show_ack: false,
          show_price: 'None',
          device: 'pos',
          profit: 1,
          amount: 1,
          title: ''
        }
      },
      qrCodeDialog: {
        show: false,
        data: null
      }
    }
  },
  computed: {
    wsMessage: function () {
      return this.websocketMessage
    }
  },
  methods: {
    openQrCodeDialog: function (lnurldevice_id) {
      var lnurldevice = _.findWhere(this.lnurldeviceLinks, {
        id: lnurldevice_id
      })
      this.qrCodeDialog.data = _.clone(lnurldevice)
      this.qrCodeDialog.data.url =
        window.location.protocol + '//' + window.location.host
      this.lnurlValue = this.qrCodeDialog.data.extra[0].lnurl
      this.websocketConnector(
        'wss://' + window.location.host + '/api/v1/ws/' + lnurldevice_id
      )
      this.qrCodeDialog.show = true
    },
    addSwitch: function () {
      if (!this.formDialoglnurldevice.data.extra) {
        this.formDialoglnurldevice.data.extra = []
      }
      this.formDialoglnurldevice.data.extra.push({
        amount: 10,
        pin: 0,
        duration: 1000,
        variable: false,
        comment: false
      })
    },
    removeSwitch: function () {
      this.formDialoglnurldevice.data.extra.pop()
    },

    cancellnurldevice: function (data) {
      var self = this
      self.formDialoglnurldevice.show = false
      self.clearFormDialoglnurldevice()
    },
    closeFormDialog: function () {
      this.clearFormDialoglnurldevice()
      this.formDialog.data = {
        is_unique: false
      }
    },
    sendFormDatalnurldevice: function () {
      var self = this
      if (!self.formDialoglnurldevice.data.profit) {
        self.formDialoglnurldevice.data.profit = 0
      }
      if (self.formDialoglnurldevice.data.id) {
        this.updatelnurldevice(
          self.g.user.wallets[0].adminkey,
          self.formDialoglnurldevice.data
        )
      } else {
        this.createlnurldevice(
          self.g.user.wallets[0].adminkey,
          self.formDialoglnurldevice.data
        )
      }
    },

    createlnurldevice: function (wallet, data) {
      var self = this
      var updatedData = {}
      for (const property in data) {
        if (data[property]) {
          updatedData[property] = data[property]
        }
      }
      LNbits.api
        .request('POST', '/lnurldevice/api/v1/lnurlpos', wallet, updatedData)
        .then(function (response) {
          self.lnurldeviceLinks.push(maplnurldevice(response.data))
          self.formDialoglnurldevice.show = false
          self.clearFormDialoglnurldevice()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    getlnurldevices: function () {
      var self = this
      LNbits.api
        .request(
          'GET',
          '/lnurldevice/api/v1/lnurlpos',
          self.g.user.wallets[0].adminkey
        )
        .then(function (response) {
          if (response.data) {
            self.lnurldeviceLinks = response.data.map(maplnurldevice)
          }
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    getatmpayments: function () {
      var self = this
      LNbits.api
        .request(
          'GET',
          '/lnurldevice/api/v1/atm',
          self.g.user.wallets[0].adminkey
        )
        .then(function (response) {
          if (response.data) {
            self.atmLinks = response.data.map(mapatmpayments)
          }
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    getlnurldevice: function (lnurldevice_id) {
      var self = this
      LNbits.api
        .request(
          'GET',
          '/lnurldevice/api/v1/lnurlpos/' + lnurldevice_id,
          self.g.user.wallets[0].adminkey
        )
        .then(function (response) {
          localStorage.setItem('lnurldevice', JSON.stringify(response.data))
          localStorage.setItem('inkey', self.g.user.wallets[0].inkey)
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    deletelnurldeviceLink: function (lnurldeviceId) {
      var self = this
      var link = _.findWhere(this.lnurldeviceLinks, {id: lnurldeviceId})
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this pay link?')
        .onOk(function () {
          LNbits.api
            .request(
              'DELETE',
              '/lnurldevice/api/v1/lnurlpos/' + lnurldeviceId,
              self.g.user.wallets[0].adminkey
            )
            .then(function (response) {
              self.lnurldeviceLinks = _.reject(
                self.lnurldeviceLinks,
                function (obj) {
                  return obj.id === lnurldeviceId
                }
              )
            })
            .catch(function (error) {
              LNbits.utils.notifyApiError(error)
            })
        })
    },
    deleteATMLink: function (atmId) {
      var self = this
      var link = _.findWhere(this.atmLinks, {id: atmId})
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this atm link?')
        .onOk(function () {
          LNbits.api
            .request(
              'DELETE',
              '/lnurldevice/api/v1/atm/' + atmId,
              self.g.user.wallets[0].adminkey
            )
            .then(function (response) {
              self.atmLinks = _.reject(self.atmLinks, function (obj) {
                return obj.id === atmId
              })
            })
            .catch(function (error) {
              LNbits.utils.notifyApiError(error)
            })
        })
    },
    openUpdatelnurldeviceLink: function (lnurldeviceId) {
      var self = this
      var lnurldevice = _.findWhere(this.lnurldeviceLinks, {
        id: lnurldeviceId
      })
      self.formDialoglnurldevice.data = _.clone(lnurldevice._data)
      if (lnurldevice.device == 'atm' && lnurldevice.extra == 'boltz') {
        self.boltzToggleState = true
      } else {
        self.boltzToggleState = false
      }
      self.formDialoglnurldevice.show = true
    },
    openlnurldeviceSettings: function (lnurldeviceId) {
      var self = this
      var lnurldevice = _.findWhere(this.lnurldeviceLinks, {
        id: lnurldeviceId
      })
      self.settingsDialog.data = _.clone(lnurldevice._data)
      self.settingsDialog.show = true
    },
    handleBoltzToggleChange(val) {
      if (val) {
        this.formDialoglnurldevice.data.extra = 'boltz'
      } else {
        this.formDialoglnurldevice.data.extra = ''
      }
    },
    updatelnurldevice: function (wallet, data) {
      var self = this
      var updatedData = {}
      for (const property in data) {
        if (data[property]) {
          updatedData[property] = data[property]
        }
      }

      LNbits.api
        .request(
          'PUT',
          '/lnurldevice/api/v1/lnurlpos/' + updatedData.id,
          wallet,
          updatedData
        )
        .then(function (response) {
          self.lnurldeviceLinks = _.reject(
            self.lnurldeviceLinks,
            function (obj) {
              return obj.id === updatedData.id
            }
          )
          self.lnurldeviceLinks.push(maplnurldevice(response.data))
          self.formDialoglnurldevice.show = false
          self.clearFormDialoglnurldevice()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    websocketConnector: function (websocketUrl) {
      if ('WebSocket' in window) {
        self = this
        var ws = new WebSocket(websocketUrl)
        self.updateWsMessage('Websocket connected')
        ws.onmessage = function (evt) {
          var received_msg = evt.data
          self.updateWsMessage('Message received: ' + received_msg)
        }
        ws.onclose = function () {
          self.updateWsMessage('Connection closed')
        }
      } else {
        self.updateWsMessage('WebSocket NOT supported by your Browser!')
      }
    },
    updateWsMessage: function (message) {
      this.websocketMessage = message
    },
    clearFormDialoglnurldevice() {
      this.formDialoglnurldevice.data = {
        lnurl_toggle: false,
        show_message: false,
        show_ack: false,
        show_price: 'None',
        title: ''
      }
    },
    exportlnurldeviceCSV: function () {
      var self = this
      LNbits.utils.exportCSV(
        self.lnurldevicesTable.columns,
        this.lnurldeviceLinks
      )
    },
    exportATMCSV: function () {
      var self = this
      LNbits.utils.exportCSV(self.atmTable.columns, this.atmLinks)
    },
    openATMLink: function (deviceid, p) {
      var self = this
      var url =
        this.location +
        '/lnurldevice/api/v1/lnurl/' +
        deviceid +
        '?atm=1&p=' +
        p
      data = {
        url: url
      }
      LNbits.api
        .request(
          'POST',
          '/lnurldevice/api/v1/lnurlencode',
          self.g.user.wallets[0].adminkey,
          data
        )
        .then(function (response) {
          window.open('/lnurldevice/atm?lightning=' + response.data)
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    }
  },
  created: function () {
    var self = this
    var getlnurldevices = this.getlnurldevices
    getlnurldevices()
    var getatmpayments = this.getatmpayments
    getatmpayments()
    self.location = [window.location.protocol, '//', window.location.host].join(
      ''
    )
    self.wslocation = ['ws://', window.location.host].join('')
    LNbits.api
      .request('GET', '/api/v1/currencies')
      .then(response => {
        this.currency = ['sat', 'USD', ...response.data]
      })
      .catch(err => {
        LNbits.utils.notifyApiError(err)
      })
  }
})
