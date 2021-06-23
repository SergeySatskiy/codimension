

def CheckServer(address):
    connect(address)
    # cml 1 rt text="Connected sucessfully?"
    # cml 1 sw
    if success:
        # cml 1 rt text="Send test request"
        testrequest()
        # cml 1 rt text="Replied OK?"
        # cml 1 sw
        if success:
            # cml 1 rt text="Report success"
            # cml 1 cc bg=#00dd00
            # cml+ fg=#ffffff
            return
        else:
            # cml 1 rt text="General failure"
            # cml 1 cc bg=#ffffff
            # cml+ fg=#ff0000
            raise
    else:
        # cml 1 rt text="Fail to connect"
        # cml 1 cc bg=#ffffff
        # cml+ fg=#ff0000
        raise
