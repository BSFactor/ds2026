import threading
import time
import sys
import uuid
from .transport import MPITransport, TAG_MSG, TAG_CMD
from .models import Message, MessageType, User

class ChatClient:
    def __init__(self, transport: MPITransport, user_id: str):
        self.transport = transport
        self.user_id = user_id
        self.rank = transport.get_rank()
        self.params = {'display_name': f'User_{self.rank}'}
        self.running = False
        self.online_users = []
        self.recv_thread = threading.Thread(target=self.listen_loop, daemon=True)

    def login(self):
        join_cmd = {
            'type': 'JOIN',
            'user': {
                'user_id': self.user_id,
                'display_name': self.params['display_name']
            }
        }
        self.transport.send(join_cmd, 0, TAG_CMD)
        self.running = True
        self.recv_thread.start()
        print(f"[Client] Logged in as {self.params['display_name']} (Rank {self.rank})")

    def send_message(self, content: str, to_user: str = 'all', use_p2p: bool = False):
        msg: Message = {
            'message_id': str(uuid.uuid4()),
            'from_user': self.user_id,
            'to_user': to_user,
            'content': content,
            'message_type': MessageType.TEXT.value,
            'timestamp': time.time()
        }
        
        # 67
        if use_p2p and to_user != 'all':
            target_rank = next((u['rank'] for u in self.online_users if u['user_id'] == to_user), None)
            if target_rank:
                try:
                    self.transport.send(msg, target_rank, TAG_MSG)
                    return
                except Exception as e:
                    self._safe_print(f"[P2P Failed]: {e}")
        
        self.transport.send(msg, 0, TAG_MSG)

    def listen_loop(self):
        while self.running:
            try:
                if self.transport.check_msg():
                    data, source, tag = self.transport.receive()
                    self.handle_incoming(data, source, tag)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"[Client Error] {e}")
                break

    def _safe_print(self, msg):
        sys.stdout.write('\r' + msg + '\n')
        sys.stdout.write('You: ')
        sys.stdout.flush()

    def send_file(self, filepath: str, to_rank: int, use_p2p: bool = False):
        import os
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            self._safe_print(f"File not found: {filepath}")
            return

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        target_id = next((u['user_id'] for u in self.online_users if u['rank'] == to_rank), None)
        
        if not target_id:
            msg = f"Rank {to_rank} not found online."
            print(msg)
            self._safe_print(msg)
            return

        file_id = str(uuid.uuid4())
        
        dest_rank = to_rank if use_p2p else 0
        tag_meta = 2
        tag_chunk = 3 
        mode_str = "P2P" if use_p2p else "Server Relay"

        try:
            # 1. Send Metadata
            meta = {
                'file_id': file_id,
                'filename': filename,
                'size': file_size,
                'from_user': self.user_id,
                'to_user': target_id
            }
            self.transport.send(meta, dest_rank, tag_meta)
            self._safe_print(f"[{mode_str}] Sending file {filename} to Rank {to_rank}...")

            # 2. Send Chunks
            CHUNK_SIZE = 1024 * 1024 # 1MB chunks
            chunk_idx = 0
            total_chunks = (file_size // CHUNK_SIZE) + 1
            
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    
                    chunk = {
                        'file_id': file_id,
                        'filename': filename,
                        'chunk_index': chunk_idx,
                        'total_chunks': total_chunks,
                        'data': data,
                        'to_user': target_id 
                    }
                    self.transport.send(chunk, dest_rank, tag_chunk)
                    chunk_idx += 1
                    time.sleep(0.001)
                    
            self._safe_print(f"File {filename} sent.")
            
        except Exception as e:
            if use_p2p:
                self._safe_print(f"[P2P Failed]: {e}.")
                self.send_file(filepath, to_rank, use_p2p=False)
            else:
                self._safe_print(f"Send failed: {e}")

    def handle_incoming(self, data, source, tag):
        if tag == TAG_MSG:
            msg: Message = data
            sender = msg['from_user']
            content = msg['content']
            type = msg['message_type']
            timestamp = time.strftime('%H:%M:%S', time.localtime(msg['timestamp']))
            
            text_to_print = ""
            if type == MessageType.SYSTEM.value:
                text_to_print = f"[SYSTEM {timestamp}] {content}"
            else:
                text_to_print = f"[{sender} {timestamp}]: {content}"
            
            self._safe_print(text_to_print)
                
        elif tag == TAG_CMD:
            cmd = data
            if cmd['type'] == 'USER_LIST_UPDATE':
                self.online_users = cmd['users']
        
        elif tag == 2: 
            meta = data
            filename = meta['filename']
            sender = meta['from_user']
            self._safe_print(f"Incoming file '{filename}' from {sender}...")
            
        elif tag == 3: 
            import os
            chunk = data
            filename = chunk['filename']
            file_data = chunk['data']
            
            os.makedirs("downloads", exist_ok=True)
            path = os.path.join("downloads", filename)
            
            with open(path, 'ab') as f:
                f.write(file_data)
                
            if chunk['chunk_index'] == chunk['total_chunks'] - 1:
                self._safe_print(f"File '{filename}' download complete (saved to downloads/).")

    def start_input_loop(self):
        print("Type a message and press Enter. Type '/quit' to exit.")
        print("Type '/users' to list online users.")
        print("Type '/dm <rank> <msg>' to send a direct message.")
        print("Type '/send <path> <rank>' to send a file.")
        
        sys.stdout.write("You: ")
        sys.stdout.flush()

        while self.running:
            try:
                inp = input() 
                sys.stdout.write("You: ")
                sys.stdout.flush()

                if inp.strip() == '/quit':
                    self.running = False
                    self.transport.send({'type': 'LEAVE'}, 0, TAG_CMD)
                    break
                
                if inp.strip() == '/users':
                    print("\n--- Online Users ---")
                    for u in self.online_users:
                        print(f"Rank {u['rank']}: {u['display_name']}")
                    sys.stdout.write("You: ")
                    sys.stdout.flush()
                    continue
                    
                if inp.startswith('/dm '):
                    parts = inp.split(' ')
                    if len(parts) >= 3:
                        try:
                            target_rank = int(parts[1])
                            
                            use_p2p = False
                            content_parts = parts[2:]
                            if "--mode" in content_parts:
                                idx = content_parts.index("--mode")
                                if idx + 1 < len(content_parts) and content_parts[idx+1].lower() == 'p2p':
                                    use_p2p = True
                                    del content_parts[idx:idx+2]
                            
                            text = " ".join(content_parts)
                            
                            target_id = next((u['user_id'] for u in self.online_users if u['rank'] == target_rank), None)
                            if target_id:
                                self.send_message(text, to_user=target_id, use_p2p=use_p2p)
                            else:
                                print("User not found.")
                        except ValueError:
                             print("Invalid rank.")
                    else:
                        print("Usage: /dm <rank> <msg> [--mode p2p]")
                    
                    continue
                
                if inp.startswith('/send '):
                    parts = inp.split(' ')
                    if len(parts) >= 3:
                        filepath = parts[1]
                        try:
                            rank = int(parts[2])
                            use_p2p = False
                            if "--mode" in parts and "p2p" in parts:
                                use_p2p = True
                            
                            threading.Thread(target=self.send_file, args=(filepath, rank, use_p2p)).start()
                        except ValueError:
                             print("Invalid rank.")
                    else:
                        print("Usage: /send <filepath> <rank> [--mode p2p]")
                    continue

                self.send_message(inp)
            except EOFError:
                break
            except Exception as e:
                print(f"Input Error: {e}")
        self.transport.close()
