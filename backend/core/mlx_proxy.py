import http.server
import http.client
import json
import socketserver
import urllib.parse
import sys
import os
import threading

# Add parent directory to path for plugin system imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# MLX Proxy - Overrides 512 token limit and handles long prefill (MoE)
# ------------------------------------------------------------------
# Plugin Sistemi Entegrasyonu
# ---------------------------
# Plugin sistemi ile entegre edilerek:
# - Model yükleme/boşaltma desteği
# - Hot-reload (sıcak yükleme) desteği
# - REST API endpoint'leri
# - Event-driven mimari

from plugin_system import PluginManager, PluginAPI, HotReloadManager

# Global plugin manager instance
_plugin_manager: PluginManager = None
_hot_reload_manager: HotReloadManager = None
_api_server_thread: threading.Thread = None


def get_plugin_manager() -> PluginManager:
    """Plugin manager instance'ını döner veya oluşturur"""
    global _plugin_manager
    if _plugin_manager is None:
        # Proxy port + 10 = Server port
        server_port = None
        if hasattr(sys, 'argv') and len(sys.argv) > 1:
            try:
                server_port = int(sys.argv[1]) + 10
            except:
                pass

        _plugin_manager = PluginManager(
            proxy_port=int(sys.argv[1]) if len(sys.argv) > 1 else 5000,
            api_port=8080
        )
    return _plugin_manager


def get_hot_reload_manager() -> HotReloadManager:
    """Hot-reload manager instance'ını döner veya oluşturur"""
    global _hot_reload_manager
    if _hot_reload_manager is None:
        _hot_reload_manager = HotReloadManager(get_plugin_manager())
    return _hot_reload_manager


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return # Silent mode

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            # Inject max_tokens: 8192
            payload = json.loads(post_data.decode('utf-8'))
            payload['max_tokens'] = 8192
            new_data = json.dumps(payload).encode('utf-8')
            
            # Forward to Real MLX Server (Port + 10)
            real_port = self.server.server_address[1] + 10
            
            conn = http.client.HTTPConnection("localhost", real_port, timeout=600)
            
            headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-length'}
            headers['Content-Length'] = str(len(new_data))
            
            conn.request("POST", self.path, body=new_data, headers=headers)
            response = conn.getresponse()
            
            # Forward response headers immediately
            self.send_response(response.status)
            for k, v in response.getheaders():
                self.send_header(k, v)
            self.end_headers()
            
            # Efficient streaming back to client
            try:
                while True:
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except BrokenPipeError:
                # Client (OpenClaude) disconnected early, no need to crash
                pass
            finally:
                conn.close()
                    
        except Exception as e:
            try:
                self.send_error(500, f"Proxy Error: {str(e)}")
            except:
                pass

    def do_GET(self):
        # Forward GET requests (like /v1/models) to real server
        real_port = self.server.server_address[1] + 10
        try:
            conn = http.client.HTTPConnection("localhost", real_port, timeout=60)
            conn.request("GET", self.path, headers=self.headers)
            response = conn.getresponse()
            
            self.send_response(response.status)
            for k, v in response.getheaders():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(response.read())
            conn.close()
        except Exception as e:
            try:
                self.send_error(500, f"Proxy Error: {str(e)}")
            except:
                pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def run_proxy(port, enable_plugin_system: bool = True):
    """Proxy sunucusunu başlatır"""
    server = ThreadedHTTPServer(('localhost', port), ProxyHandler)
    print(f"[*] Proxy running on port {port} (Forwarding to {port+10})")

    if enable_plugin_system:
        # Plugin sistemini başlat
        pm = get_plugin_manager()

        # API sunucusunu başlat
        pm.start_api_server()
        print(f"[*] Plugin API running on port 8080")

        # Hot-reload manager'ı başlat
        hrm = get_hot_reload_manager()
        hrm.start()
        print(f"[*] Hot-reload monitoring enabled")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")

        if enable_plugin_system:
            # Temizleme
            pm = get_plugin_manager()
            hrm = get_hot_reload_manager()

            hrm.stop()
            pm.stop_api_server()
            pm.stop_watcher()

        server.shutdown()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mlx_proxy.py <port> [--no-plugin]")
        sys.exit(1)

    port = int(sys.argv[1])
    enable_plugin = "--no-plugin" not in sys.argv

    run_proxy(port, enable_plugin_system=enable_plugin)
