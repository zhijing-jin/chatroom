def query(msg_str, sockfd, recv_size=1000):
    msg = str.encode(msg_str)
    sockfd.send(msg)
    rmsg = sockfd.recv(recv_size)
    return rmsg
