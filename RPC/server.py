import grpc
from concurrent import futures
import time
import os
import file_transfer_pb2
import file_transfer_pb2_grpc

class FileTransferServicer(file_transfer_pb2_grpc.FileTransferServicer):
    def UploadFile(self, request_iterator, context):
        filename = None
        
        try:
            first_request = next(request_iterator)
            if first_request.HasField('metadata'):
                filename = first_request.metadata.filename

                filename = os.path.basename(filename)
                
                upload_dir = 'received_files'
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                filepath = os.path.join(upload_dir, filename)
                print(f"Server: Start receiving file: {filename} -> {filepath}")
            else:
                return file_transfer_pb2.UploadResponse(
                    message="First message must be metadata containing filename", 
                    success=False
                )
            
            with open(filepath, 'wb') as f:
                for request in request_iterator:
                    if request.HasField('chunk'):
                        f.write(request.chunk)
                    else:
                        pass
                        
            print(f"Server: Received file {filename} successfully.")
            return file_transfer_pb2.UploadResponse(
                message=f"File {filename} uploaded successfully", 
                success=True
            )
            
        except Exception as e:
            print(f"Server: Error receiving file: {e}")
            return file_transfer_pb2.UploadResponse(
                message=str(e), 
                success=False
            )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    file_transfer_pb2_grpc.add_FileTransferServicer_to_server(FileTransferServicer(), server)
    port = 50051
    server.add_insecure_port(f'[::]:{port}')
    print(f"Server started on port {port}")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()