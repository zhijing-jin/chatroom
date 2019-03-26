#!/usr/bin/python

import socket
import sys
import select

def main(argv):
	# set port number
	# default is 32342 if no input argument
	if len(argv) == 2:
		port = int(argv[1])
	else:
		port = 32342

	# create socket and bind
	sockfd = socket.socket()
	try:
		sockfd.bind(('', port))
	except socket.error as emsg:
		print("Socket bind error: ", emsg)
		sys.exit(1)

	# set socket listening queue
	sockfd.listen(5)

	# add the listening socket to the READ socket list
	RList = [sockfd]

	# create an empty WRITE socket list
	WList = []

	# start the main loop
	while True:
		# use select to wait for any incoming connection requests or
		# incoming messages or 10 seconds
		try:
			Rready, Wready, Eready = select.select(RList, [], [], 10)
			print(Rready, Wready, Eready, 0)
		except select.error as emsg:
			print("At select, caught an exception:", emsg)
			sys.exit(1)
		except KeyboardInterrupt:
			print("At select, caught the KeyboardInterrupt")
			sys.exit(1)

		# if has incoming activities
		if Rready:
			print(Rready, Wready, Eready, 1)
			# for each socket in the READ ready list
			for sd in Rready:

				# if the listening socket is ready
				# that means a new connection request
				# accept that new connection request
				# add the new client connection to READ socket list
				# add the new client connection to WRITE socket list
				if sd == sockfd:
					newfd, caddr = sockfd.accept()
					print("A new client has arrived. It is at:", caddr)
					RList.append(newfd)
					WList.append(newfd)

				# else is a client socket being ready
				# that means a message is waiting or
				# a connection is broken
				# if a new message arrived, send to everybody
				# except the sender
				# if broken connection, remove that socket from READ
				# and WRITE lists
				else:
					rmsg = sd.recv(500)
					if rmsg:
						print("Got a message!!")
						if len(WList) > 1:
							print("Relay it to others.")
							for p in WList:
								if p != sd:
									p.send(rmsg)
					else:
						print("A client connection is broken!!")
						WList.remove(sd)
						RList.remove(sd)

		# else did not have activity for 10 seconds,
		# just print out "Idling"
		else:
			print("Idling")


if __name__ == '__main__':
	if len(sys.argv) > 2:
		print("Usage: chatserver [<Server_port>]")
		sys.exit(1)
	main(sys.argv)
