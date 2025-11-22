import socket
import sys
import os

def send_file(server_ip, port, filename):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        server_address = (server_ip, port)
        print(f'Connecting to {server_ip} port {port}...')
        client_socket.connect(server_address)
        
        print(f'Sending filename: {filename}')
        client_socket.sendall(filename.encode('utf-8'))
        
        ack = client_socket.recv(1024)
        if ack.decode('utf-8') != 'ACK':
            print('Server did not acknowledge filename.')
            return
            
        print('Server acknowledged. Sending file data...')
        
        with open(filename, 'rb') as f:
            while True:
                data = f.read(1024)
                if not data:
                    break
                client_socket.sendall(data)
                
        print('File sent successfully.')
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <server_ip> <port> <filename>")
        sys.exit(1)
        
    server_ip = sys.argv[1]
    port = int(sys.argv[2])
    filename = sys.argv[3]
    
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
        
    send_file(server_ip, port, filename)
