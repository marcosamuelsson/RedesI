import socket
import threading
import select

SOCKS_VERSION = 5

class Proxy:
    def __init__(self):
        self.username = 'user'
        self.password = 'password'
    
    def handle_client(self, connection):
        version, nmethodes = connection.recv(2)

        methodes = self.get_avaible_methodes(nmethodes, connection)

        if 2 not in set(methodes):
            connection.close()
            return
        
        connection.sendall(bytes([SOCKS_VERSION, 2]))

        if not self.verify_credentials(connection):
            return
        
        version, cmd, _, address_type = connection.recv(4)

        if address_type == 1:
            address = socket.inet_ntoa(connection.recv(4))
        elif address_type == 3:
            domain_len = connection.recv(1)[0]
            address = connection.recv(domain_len)
            address = socket.gethostbyname(address)
        port = int.from_bytes(connection.recv(2), 'big', signed=False)

        try:
            if cmd == 1:
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((address, port))
                bind_addresss = remote.getsockname()
                print("* Connected to {} {}".format_map(address, port))
            else:
                connection.close()
            
            addr = int.from_bytes(socket.inet_aton(bind_addresss[0], 'big', signed=False))
            port = bind_addresss[1]

            reply = b''.join([
                SOCKS_VERSION.to_bytes(1, 'big'),
                int(0).to_bytes(1, 'big'),
                int(0).to_bytes(1, 'big'),
                int(1).to_bytes(1, 'big'),
                addr.to_bytes(4, 'big'),
                port.to_bytes(2, 'big'),
            ])
        except Exception as e:
            reply = self.generate_failed_reply(address_type, 5)

        connection.sendall(reply)

        if reply[1] == 0 and cmd == 1:
            self.exchange_loop(connection, remote)
        
        connection.close()
    
    def exchange_loop(self, client, remote):
        while True:
            r, w, e = select.select([client, remote], [], [])

            if client in r:
                data = client.recv(4096)
                if remote.send(data) <= 0:
                    break
            if remote in r:
                data = remote.recv(4096)
                if client.send(data) <= 0:
                    break

    def generate_failed_reply(self, address_type, error_number):
        return b''.join([
                SOCKS_VERSION.to_bytes(1, 'big'),
                error_number.to_bytes(1, 'big'),
                int(0).to_bytes(1, 'big'),
                address_type.to_bytes(1, 'big'),
                int(0).to_bytes(1, 'big'),
                int(1).to_bytes(1, 'big'),
            ])
    def verify_credentials(self, connection):
        version = ord(connection.recv(1))

        usernamelen = ord(connection.recv(1))
        username = connection.recv(usernamelen).decode('utf-8')

        paswordlen = ord(connection.recv(1))
        password = connection.recv(paswordlen).decode('utf-8')

        if username == self.username and password == self.password:
            response = bytes([version, 0])
            connection.sendall(response)
            return True

        response = bytes([version, 0xFF])
        connection.sendall(response)
        connection.close()
        return False
    
    def get_avaible_methodes(self, nmethodes, connection):
        methodes = []
        for i in range(nmethodes):
            methodes.append(ord(connection.recv(1)))
        return methodes
    
    def run(self, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, port))
        s.listen()

        print("* Socks5 proxy server is running on {}:{}".format(host, port))
        while True:
            conn, addr = s.accept()
            print("* new conncetion from {}".format(addr))
            t = threading.Thread(target=self.handle_client, args=(conn,))
            t.start()


if __name__ == '__main__':
    proxy = Proxy()
    proxy.run("127.0.0.1", 3000)