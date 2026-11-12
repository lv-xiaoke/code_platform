export function trackBrowserTab() {
  let socket: WebSocket | undefined
  let retry: number | undefined

  function open() {
    if (socket) return
    const connection = new WebSocket(`ws://${location.host}/api/v1/browser-tab`)
    socket = connection
    connection.addEventListener('close', event => {
      if (socket !== connection) return
      socket = undefined
      // A server started with -NoBrowser closes normally as soon as it connects.
      if (event.code !== 1000) retry = window.setTimeout(open, 1000)
    })
  }

  window.addEventListener('pageshow', open)
  window.addEventListener('pagehide', () => {
    window.clearTimeout(retry)
    const connection = socket
    socket = undefined
    connection?.close()
  })
  open()
}
