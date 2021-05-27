import socket

if __name__ == "__main__":

    for _ in range(10000):
        address_info = socket.getaddrinfo('qx-020020.phabrix.local', 0)

    print('No exceptions thrown')
