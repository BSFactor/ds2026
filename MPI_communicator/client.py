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

    def send_message(self, content: str, to_user: str = 'all'):
        msg: Message = {
            'message_id': str(uuid.uuid4()),
            'from_user': self.user_id,
            'to_user': to_user,
            'content': content,
            'message_type': MessageType.TEXT.value,
            'timestamp': time.time()
        }
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

    def start_input_loop(self):
        print("Type a message and press Enter. Type '/quit' to exit.")
        print("Type '/users' to list online users.")
        print("Type '/dm <rank> <msg>' to send a direct message.")
        
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
                    parts = inp.split(' ', 2)
                    if len(parts) >= 3:
                        target_rank = int(parts[1])
                        text = parts[2]
                        target_id = next((u['user_id'] for u in self.online_users if u['rank'] == target_rank), None)
                        if target_id:
                            self.send_message(text, to_user=target_id)
                        else:
                            print("User not found.")
                    else:
                        print("Usage: /dm <rank> <msg>")
                    
                    sys.stdout.write("You: ")
                    sys.stdout.flush()
                    continue

                self.send_message(inp)
            except EOFError:
                break
            except Exception as e:
                print(f"Input Error: {e}")
        self.transport.close()
