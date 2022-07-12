from test.web.parrot_webserver import ParrotWebServer


def make_fake_tpbd() -> ParrotWebServer:
    server = ParrotWebServer()
    # start setting up the server
    # server.set_response( url, bytearray())
    return server
