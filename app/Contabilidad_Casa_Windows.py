#!/usr/bin/env python3
"""Ventana nativa para Contabilidad Casa V0.3.9 (Windows, WebView2)."""
from __future__ import annotations

import threading
import traceback
import sys


def _fatal(message):
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, str(message), 'Contabilidad Casa', 0x10)
    else:
        print(message, file=sys.stderr)


def main():
    server = None
    try:
        import webview
        import Contabilidad_Casa as app
        from perfiles import Profiles
        from http.server import ThreadingHTTPServer

        # Sin contabilidad predeterminada: si no hay datos existentes,
        # la pantalla muestra la lista VACÍA y el botón para crear/importar.
        app.PROFILES = Profiles(app.ROOT)
        current = app.PROFILES.selected()
        if current:
            app._activate_profile(current)

        server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        server.daemon_threads = True
        server_thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval':0.2}, daemon=True)
        server_thread.start()
        url = f'http://127.0.0.1:{server.server_address[1]}/'

        # Ventana MAXIMIZADA, con barra y botones normales de Windows.
        # No es pantalla completa exclusiva ni navegador con pestañas.
        window = webview.create_window('Contabilidad Casa V0.3.9', url,
                                       width=1200, height=800, min_size=(900, 600),
                                       maximized=True, background_color='#F5F7FB')
        window.events.shown += lambda: window.maximize()
        # WebView2 únicamente, sin recurrir al motor obsoleto de Internet Explorer.
        webview.start(gui='edgechromium', debug=False)
    except Exception as e:
        _fatal('No se ha podido iniciar Contabilidad Casa.\n\n'
               + str(e) + '\n\n'
               + 'Si falta WebView2, instálalo desde la web oficial de Microsoft.')
        traceback.print_exc()
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
