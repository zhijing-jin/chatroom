#!/usr/bin/python3

import socket
import sys


def build_socket(server, port):
    # create socket and connect to Comm_pipe
    try:
        sockfd = socket.socket()
        sockfd.connect((server, port))
    except socket.error as emsg:
        print("Socket error: ", emsg)
        sys.exit(1)

    # once the connection is established; print out
    # the socket addresses of your local socket and
    # the Comm_pipe
    print("[Info] Connection established.")
    print("[Info] My socket address is", sockfd.getsockname())
    print("[Info] Comm_pipe socket address is", sockfd.getpeername())

    return sockfd
