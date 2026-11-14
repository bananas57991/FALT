import asyncio
import logging
import sys
import os
import io

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 80  # Requires sudo privileges to run on Linux port 80

DECODER_FILE = "faltlink_dual_decoder_v2.py"
_repo_decode_function = None

def load_native_decoder():
    global _repo_decode_function
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)
    try:
        import faltlink_dual_decoder_v2
        if hasattr(faltlink_dual_decoder_v2, 'decode'):
            _repo_decode_function = getattr(faltlink_dual_decoder_v2, 'decode')
            logging.info("Successfully bound 'decode' engine module.")
        elif hasattr(faltlink_dual_decoder_v2, 'decode'):
            _repo_decode_function = getattr(faltlink_dual_decoder_v2, 'decode')
            logging.info("Successfully bound 'decode' engine module.")
    except Exception as err:
        logging.critical(f"Cannot initialize decoder backend: {err}")
        sys.exit(1)

load_native_decoder()

async def handle_falt_request(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
    try:
        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = await client_reader.read(4096)
            if not chunk: break
            header_data += chunk

        if not header_data:
            client_writer.close()
            return

        header_text = header_data.decode('utf-8', errors='ignore')
        header_lines = header_text.split('\r\n')
        req_parts = header_lines[0].split()
        
        if len(req_parts) < 2:
            client_writer.close()
            return

        method, full_path, http_version = req_parts[0], req_parts[1], req_parts[2]
        
        path_segments = [seg for seg in full_path.split('/') if seg]
        if not path_segments:
            client_writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\nMissing URL Path Elements")
            client_writer.close()
            return

        target_string_payload = path_segments[0]

        if '.' not in target_string_payload or target_string_payload.endswith(('.html', '.ico', '.css', '.js', '.png', '.jpg', '.svg')):
            client_writer.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nResource Uncached")
            await client_writer.drain()
            client_writer.close()
            return

        # Isolate the clean domain name text token out of the string block context
        # e.g., "OjozBPFKtSyDViVA1RWi2Ye2.ftest" -> "ftest"
        clean_target_domain = target_string_payload.split('.', 1)[1] if '.' in target_string_payload else "localhost"

        if not target_string_payload.startswith('+'):
            target_string_payload = '' + target_string_payload

        # Capture the text string printed by your script file to recover the network address
        logging.info(f"Passing complete string payload to decoder module -> '{target_string_payload}'")
        
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            returned_value = _repo_decode_function(target_string_payload)
        finally:
            sys.stdout = old_stdout
            
        print_history = captured_output.getvalue()
        
        decrypted_host = None
        for line in print_history.split('\n'):
            if "Decoded IP:Port:" in line:
                decrypted_host = line.split("Decoded IP:Port:")[-1].strip()
                break

        if not decrypted_host and returned_value and str(returned_value).strip() != "None":
            decrypted_host = str(returned_value).strip()

        if not decrypted_host:
            logging.error("Could not capture a valid decrypted host address string from print output streams.")
            client_writer.write(b"HTTP/1.1 500 Internal Error\r\n\r\nDecryption Capture Failure")
            client_writer.close()
            return

        logging.info(f"Captured clean address string from print tracker: '{decrypted_host}'")

        if ':' in decrypted_host:
            remote_ip, port_raw = decrypted_host.rsplit(':', 1)
            remote_ip = remote_ip.replace('[', '').replace(']', '').strip()
            remote_port = int("".join([c for c in port_raw if c.isdigit()]))
        else:
            remote_ip, remote_port = decrypted_host, 80

        logging.info(f"FALT Tunnel established: Forwarding directly to host -> [{remote_ip}]:{remote_port}")

        # Clean down path arguments to strip out the prefix chunk layout folder before hitting Nginx
        clean_path = "/" + "/".join(path_segments[1:]) if len(path_segments) > 1 else "/"

        # REVISED: Inject the clean, stripped target domain text parameter directly into the Host header
        new_headers = f"{method} {clean_path} {http_version}\r\n"
        new_headers += f"Host: {clean_target_domain}\r\n"
        
        for line in header_lines[1:]:
            if line.strip() and not line.lower().startswith("host:"):
                new_headers += line + "\r\n"
        new_headers += "\r\n"

        remote_reader, remote_writer = await asyncio.open_connection(remote_ip, remote_port)
        remote_writer.write(new_headers.encode())
        await remote_writer.drain()

        async def pipe(src, dst):
            try:
                while True:
                    data = await src.read(8192)
                    if not data: break
                    dst.write(data)
                    await dst.drain()
            except Exception: pass
            finally: dst.close()

        await asyncio.gather(
            pipe(client_reader, remote_writer),
            pipe(remote_reader, client_writer)
        )
    except Exception as e:
        logging.error(f"Proxy networking pipeline exception encountered: {e}")
        try: client_writer.close()
        except Exception: pass

async def main():
    server = await asyncio.start_server(handle_falt_request, LISTEN_HOST, LISTEN_PORT)
    logging.info(f"Direct FALT Routing Daemon successfully listening on {LISTEN_HOST}:{LISTEN_PORT}")
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Halted.")

