import grpc
import os
import sys

import file_transfer_pb2
import file_transfer_pb2_grpc

SERVER_IP = '127:0:0:1'
PORT = 50051
CHUNK_SIZE = 1024 * 1024

def file_chunk_generator(filename):
    yield file_transfer_pb2.UploadRequest(
        metadata=file_transfer_pb2.MetaData(filename=os.path.basename(filename))
    )
    try:
        with open(filename, 'rb') as f:
            while True:
                chunk_data = f.read(CHUNK_SIZE)
                if not chunk_data:
                    break
                yield file_transfer_pb2.UploadRequest(chunk=chunk_data)
                
    except Exception as e:
        print(f"Error reading file: {e}")
        raise

def run_client(server_ip, port, filename):
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)

    try:
        with grpc.insecure_channel(f'{server_ip}:{port}') as channel:
            stub = file_transfer_pb2_grpc.FileTransferStub(channel)
            
            print(f"Uploading file: {filename}...")
            
            response = stub.UploadFile(file_chunk_generator(filename))
            
            if response.success:
                print(f"Success: {response.message}")
            else:
                print(f"Failed: {response.message}")
                
    except grpc.RpcError as e:
        print(f"gRPC Error: {e.details()}")
    except Exception as e:
        print(f"Client Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filename>")
        sys.exit(1)
        
    filename_to_send = sys.argv[1]
    run_client(SERVER_IP, PORT, filename_to_send)