import socket
import sys
import os

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    server_address = ('', port)
    print(f'Starting server on port {port}...')
    server_socket.bind(server_address)
    
    server_socket.listen(1)
    
    while True:
        print('Waiting for a connection...')
        connection, client_address = server_socket.accept()
        try:
            print(f'Connection from {client_address}')
            
            data = connection.recv(1024)
            if data:
                filename = data.decode('utf-8')
                print(f'Receiving file: {filename}')
                
                connection.sendall(b'ACK')
                
                with open(filename, 'wb') as f:
                    while True:
                        data = connection.recv(1024)
                        if not data:
                            break
                        f.write(data)
                
                print(f'File {filename} received successfully.')
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            connection.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)
        
    port = int(sys.argv[1])
    start_server(port)
