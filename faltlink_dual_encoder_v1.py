import hashlib
import base64
import socket

def main():
    domain_name = input("Enter the domain name (without TLD): ")
    ip_port = input("Enter the IP:Port (e.g., 192.168.1.1:80 or [2001:db8::1]:80): ")

    # Step 1: Hash the domain name and get the truncated 8-byte result
    domain_bytes = domain_hash(domain_name)

    # Step 2: Convert IP:Port to 8-byte binary data
    ip_port_bytes = ip_port_to_bin(ip_port)

    # Step 3: XOR the byte sequences
    xor_result = xor_bytes(domain_bytes, ip_port_bytes)

    # Step 4: Convert the XOR result to base64 and format it
    base64_result = bin_to_base64(xor_result)

    # Step 5: Append the base64 result with the original domain name
    final_result = f"{base64_result}.{domain_name}"

    print("Result:", final_result)


#step one logic:

def domain_hash(domain_name):
    # Hash the domain name using SHA-1
    sha1_hash = hashlib.sha1(domain_name.encode()).digest()
    # Truncate to 8 bytes (64 bits)
    truncated_bytes = sha1_hash[:18]
    return truncated_bytes

#step two logic:

def ip_port_to_bin(ip_port):
    ip, port = ip_port.rsplit(':', 1)
    
    try:
        # Try to convert IP to binary (IPv4 or IPv6)
        ip_bin = socket.inet_pton(socket.AF_INET, ip)  # Try IPv4
        ip_bits = 32
    except OSError:
        ip_bin = socket.inet_pton(socket.AF_INET6, ip)  # Try IPv6
        ip_bits = 128
    
    # Convert Port to binary
    port_bin = int(port).to_bytes(2, byteorder='big')
    
    # Combine IP and Port binary data
    ip_port_bytes = ip_bin + port_bin

    # Truncate or pad to fit into 8 bytes (64 bits)
    if ip_bits == 32:  # IPv4
        ip_port_bytes = ip_port_bytes.rjust(6)  # Pad the left side with zeros
    else:  # IPv6
        ip_port_bytes = ip_port_bytes[:18] + port_bin  # Truncate the IP to 6 bytes

    return ip_port_bytes


#step three logic:

def xor_bytes(bytes1, bytes2):
    # XOR two byte sequences
    return bytes(a ^ b for a, b in zip(bytes1, bytes2))


#step four logic:

def bin_to_base64(byte_data):
    # Convert bytes to base64 and remove padding
    base64_encoded = base64.b64encode(byte_data).decode().rstrip('=')
    return base64_encoded



if __name__ == "__main__":
    main()



