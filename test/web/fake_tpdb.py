from test.web.parrot_webserver import ParrotWebserver


def make_fake_tpbd() -> ParrotWebserver:
    server = ParrotWebserver()
    # start setting up the server
    # server.set_response( url, bytearray())
    return server
