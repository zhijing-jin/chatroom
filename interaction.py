def query(msg_str, sockfd, recv_size=1000):
    msg = str.encode(msg_str)
    sockfd.send(msg)
    rmsg = sockfd.recv(recv_size).decode("utf-8")
    if rmsg == 'F:error message::\r\n':
        print("[Error] F:error message")

    return rmsg

def parse_rmsg(msg_str, prefix="G:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n

    assert msg_str.startswith(prefix), "Groups must start with {}".format(prefix)
    assert msg_str.endswith(suffix), "Groups must end with {}".format(suffix)
    msg_str = msg_str[len(prefix): -len(suffix)]
    return msg_str.split(':')

def parse_members(msg_str, prefix="M:", suffix="::\r\n"):
    msg = parse_rmsg(msg_str, prefix=prefix, suffix=suffix)
    

def parse_memberships(msg_str, prefix="M:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n

    assert msg_str.startswith(prefix), "Memberships must start with {}".format(prefix)
    assert msg_str.endswith(suffix), "Memberships must end with {}".format(suffix)
    msg_str = msg_str[len(prefix): -len(suffix)]

    # user_ID:IP:port
    return msg_str.split(':')
