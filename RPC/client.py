import grpc
import sys
import os
import file_transfer_pb2
import file_transfer_pb2_grpc

CHUNK_SIZE = 1024 * 1024

def generate_requests(filename):
    metadata = file_transfer_pb2.MetaData(filename=os.path.basename(filename))
    yield file_transfer_pb2.UploadRequest(metadata=metadata)
    
    with open(filename, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            yield file_transfer_pb2.UploadRequest(chunk=chunk)

def run(server_address, filename):
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return

    print(f"Connect to {server_address}")
    with grpc.insecure_channel(server_address) as channel:
        stub = file_transfer_pb2_grpc.FileTransferStub(channel)
        
        print(f"Starting upload {filename}...")
        try:
            response = stub.UploadFile(generate_requests(filename))
            print(f"Server message: {response.message}")
        except grpc.RpcError as e:
            print(f"RPC failed: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(1)
        
    server_address = sys.argv[1]
    filename = sys.argv[2]
    
    run(server_address, filename)