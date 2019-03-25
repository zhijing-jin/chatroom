def query(msg_str, sockfd, recv_size=1000):
    msg = str.encode(msg_str)
    sockfd.send(msg)
    rmsg = sockfd.recv(recv_size)
    if rmsg == 'F:error message::\r\n':
        print("[Error] F:error message")
    return rmsg


def parse_groups(msg_str, prefix="G:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n

    assert msg_str.startswith(prefix)
    assert msg_str.endswith(suffix)
    msg_str = msg_str[len(prefix): -len(suffix)]
    return msg_str.split(':')
