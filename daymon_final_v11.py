import asyncio
import logging
import sys
import os
import io
import socket

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

def execute_stateless_decryption(raw_path_segment: str) -> tuple[str, int]:
    try:
        logging.info(f"Invoking decoder module for raw prefix token -> '{raw_path_segment}'")
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            returned_value = _repo_decode_function(raw_path_segment)
        except Exception as e:
            logging.error(f"Internal execution error inside decoder module: {e}")
            returned_value = None
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

        if decrypted_host:
            if ':' in decrypted_host:
                parts = decrypted_host.rsplit(':', 1)
                ip_part = parts[0].replace('[', '').replace(']', '').strip()
                port_part = parts[1]
                clean_port = "".join([c for c in port_part if c.isdigit()])
                return ip_part, int(clean_port) if clean_port else 80
            else:
                return decrypted_host, 80
    except Exception as err:
        logging.error(f"Decryption translation processing loop error: {err}")
    return None, None

async def handle_falt_request(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
    try:
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            chunk = await client_reader.read(4096)
            if not chunk: break
            buffer += chunk

        if not buffer or b"\r\n\r\n" not in buffer:
            client_writer.close()
            return

        # FIXED: Accurately split headers from the consumed body payload data
        header_data, body_remainder = buffer.split(b"\r\n\r\n", 1)

        header_text = header_data.decode('utf-8', errors='ignore')
        header_lines = header_text.split('\r\n')
        req_parts = header_lines[0].split()
        
        if len(req_parts) < 2:
            client_writer.close()
            return

        method, full_path, http_version = req_parts[0], req_parts[1], req_parts[2]
        path_segments = [seg for seg in full_path.split('/') if seg]
        
        if not path_segments:
            client_writer.write(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\nEmpty Request Suffix")
            client_writer.close()
            return

        target_string_payload = path_segments[0]

        if '.' not in target_string_payload or target_string_payload.endswith(('.html', '.ico', '.css', '.js', '.png', '.jpg', '.svg')):
            client_writer.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nResource Uncached")
            await client_writer.drain()
            client_writer.close()
            return

        clean_target_domain = target_string_payload.split('.', 1)[1] if '.' in target_string_payload else "localhost"
        remote_ip, remote_port = execute_stateless_decryption(target_string_payload)

        if not remote_ip or remote_ip == "127.0.0.1":
            logging.warning(f"Aborting connection: Unresolvable host endpoint structure for token: {target_string_payload}")
            client_writer.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nFALT Host Destination Unresolvable")
            await client_writer.drain()
            client_writer.close()
            return

        logging.info(f"Routing traffic live to true decrypted endpoint -> [{remote_ip}]:{remote_port}")

        clean_path = "/" + "/".join(path_segments[1:]) if len(path_segments) > 1 else "/"

        new_headers = f"{method} {clean_path} {http_version}\r\n"
        new_headers += f"Host: {clean_target_domain}\r\n"
        new_headers += "Connection: close\r\n"
        
        for line in header_lines[1:]:
            if line.strip():
                lower_line = line.lower()
                if not lower_line.startswith("host:") and not lower_line.startswith("connection:"):
                    new_headers += line + "\r\n"
        new_headers += "\r\n"

        if ":" in remote_ip:
            remote_reader, remote_writer = await asyncio.open_connection(
                host=remote_ip, 
                port=remote_port,
                family=socket.AF_INET6
            )
        else:
            remote_reader, remote_writer = await asyncio.open_connection(remote_ip, remote_port)

        # FIXED: Forward the rebuilt headers PLUS the captured body remainder packet together
        remote_writer.write(new_headers.encode() + body_remainder)
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
        logging.error(f"Proxy networking pipeline error: {e}")
        try: client_writer.close()
        except Exception: pass

async def main():
    server = await asyncio.start_server(handle_falt_request, LISTEN_HOST, LISTEN_PORT)
    logging.info(f"Stateless Full-Body Multiplexing FALT Daemon active on {LISTEN_HOST}:{LISTEN_PORT}")
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Halted.")
