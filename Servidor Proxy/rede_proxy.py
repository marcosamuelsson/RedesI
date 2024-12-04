import socket
import threading
import select

# Define a versão do protocolo SOCKS utilizada.
SOCKS_VERSION = 5

class Proxy:
    def __init__(self):
        # Credenciais básicas de autenticação.
        self.username = 'user'
        self.password = 'password'
    
    def handle_client(self, connection):
        # Recebe a versão do protocolo e o número de métodos de autenticação suportados.
        version, nmethodes = connection.recv(2)

        # Obtém os métodos de autenticação disponíveis enviados pelo cliente.
        methodes = self.get_avaible_methodes(nmethodes, connection)

        # Verifica se o método de autenticação "2" (usuário/senha) está disponível.
        if 2 not in set(methodes):
            connection.close()  # Fecha a conexão se não estiver disponível.
            return
        
        # Envia a resposta indicando que o método de autenticação por usuário/senha será usado.
        connection.sendall(bytes([SOCKS_VERSION, 2]))

        # Verifica as credenciais do cliente.
        if not self.verify_credentials(connection):
            return
        
        # Recebe o cabeçalho do pedido do cliente (versão, comando, reservado e tipo de endereço).
        version, cmd, _, address_type = connection.recv(4)

        # Processa o endereço solicitado dependendo do tipo (IPv4 ou domínio).
        if address_type == 1:  # IPv4
            address = socket.inet_ntoa(connection.recv(4))
        elif address_type == 3:  # Nome de domínio
            domain_len = connection.recv(1)[0]
            address = connection.recv(domain_len)
            address = socket.gethostbyname(address)
        # Recebe a porta solicitada.
        port = int.from_bytes(connection.recv(2), 'big', signed=False)

        try:
            if cmd == 1:  # Comando 1: Conexão TCP.
                # Cria o socket para conexão com o servidor remoto.
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((address, port))
                bind_addresss = remote.getsockname()
                print("* Connected to {} {}".format_map(address, port))
            else:
                connection.close()
            
            # Constrói a resposta indicando que a conexão foi bem-sucedida.
            addr = int.from_bytes(socket.inet_aton(bind_addresss[0], 'big', signed=False))
            port = bind_addresss[1]

            reply = b''.join([
                SOCKS_VERSION.to_bytes(1, 'big'),
                int(0).to_bytes(1, 'big'),  # Código de sucesso.
                int(0).to_bytes(1, 'big'),
                int(1).to_bytes(1, 'big'),  # IPv4.
                addr.to_bytes(4, 'big'),
                port.to_bytes(2, 'big'),
            ])
        except Exception as e:
            # Gera uma resposta de erro em caso de falha.
            reply = self.generate_failed_reply(address_type, 5)

        # Envia a resposta ao cliente.
        connection.sendall(reply)

        # Inicia a troca de dados entre cliente e servidor remoto se a conexão foi bem-sucedida.
        if reply[1] == 0 and cmd == 1:
            self.exchange_loop(connection, remote)
        
        connection.close()  # Fecha a conexão após finalizar.
    
    def exchange_loop(self, client, remote):
        # Realiza a troca de dados entre o cliente e o servidor remoto.
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
        # Gera uma resposta de erro para o cliente.
        return b''.join([
                SOCKS_VERSION.to_bytes(1, 'big'),
                error_number.to_bytes(1, 'big'),
                int(0).to_bytes(1, 'big'),
                address_type.to_bytes(1, 'big'),
                int(0).to_bytes(1, 'big'),
                int(1).to_bytes(1, 'big'),
            ])
    
    def verify_credentials(self, connection):
        # Verifica as credenciais enviadas pelo cliente.
        version = ord(connection.recv(1))

        usernamelen = ord(connection.recv(1))
        username = connection.recv(usernamelen).decode('utf-8')

        paswordlen = ord(connection.recv(1))
        password = connection.recv(paswordlen).decode('utf-8')

        if username == self.username and password == self.password:
            # Responde com sucesso se as credenciais estiverem corretas.
            response = bytes([version, 0])
            connection.sendall(response)
            return True

        # Responde com erro se as credenciais estiverem incorretas.
        response = bytes([version, 0xFF])
        connection.sendall(response)
        connection.close()
        return False
    
    def get_avaible_methodes(self, nmethodes, connection):
        # Obtém os métodos de autenticação disponíveis enviados pelo cliente.
        methodes = []
        for i in range(nmethodes):
            methodes.append(ord(connection.recv(1)))
        return methodes
    
    def run(self, host, port):
        # Inicia o servidor proxy.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, port))
        s.listen()

        print("* Socks5 proxy server is running on {}:{}".format(host, port))
        while True:
            conn, addr = s.accept()
            print("* new conncetion from {}".format(addr))
            # Cria uma nova thread para tratar o cliente.
            t = threading.Thread(target=self.handle_client, args=(conn,))
            t.start()

if __name__ == '__main__':
    # Instancia o proxy e o executa no endereço e porta especificados.
    proxy = Proxy()
    proxy.run("127.0.0.1", 3000)