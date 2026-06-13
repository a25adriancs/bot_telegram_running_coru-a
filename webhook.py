import json
import asyncio
from http.server import BaseHTTPRequestHandler
from bot.main import application, handle_webhook

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update_data = json.loads(post_data.decode('utf-8'))
        
        # Ejecutamos la lógica de procesamiento del bot
        loop = asyncio.get_event_loop()
        loop.run_until_complete(handle_webhook(update_data))
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write('OK'.encode('utf-8'))
        return
