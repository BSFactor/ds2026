import grpc
import time
import concurrent.futures

import file_transfer_pb2
import file_transfer_pb2_grpc

MAX_WORKERS = 10
PORT = 50051

class FileTransferServicer(file_transfer_pb2_grpc.FileTransferServicer):
    
    def UploadFile(self, request_iterator, context):
        filename = None
        file_data_written = 0
        
        try:
            for chunk in request_iterator:
                if filename is None:
                    filename = chunk.metadata
                    print(f"Receiving file: {filename}")
                    
                if chunk.chunk:
                    with open(filename, 'ab') as f:
                        f.write(chunk.chunk)
                    file_data_written += len(chunk.chunk)
            
            print(f"File {filename} received successfully. Total bytes: {file_data_written}")
            return file_transfer_pb2.UploadStatus(success=True, message=f"File {filename} received.")
        except Exception as e:
            print(f"Error during file upload: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"An error occurred on the server: {e}")
            return file_transfer_pb2.UploadStatus(success=False, message=f"Upload failed: {e}")

def serve():
    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    
    file_transfer_pb2_grpc.add_FileTransferServicer_to_server(
        FileTransferServicer(), server)
        
    server.add_insecure_port(f'[::]:{PORT}')
    server.start()
    print(f"Server started, listening on port {PORT}...")
    
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)
        print("Server stopped.")

if __name__ == '__main__':
    serve()