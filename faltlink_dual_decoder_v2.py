import hashlib
import base64
import socket

def main():
    encoded_string = input("Enter the encoded string (format: base64.domain_name): ")

    # Step 1: Extract the base64 encoded XOR result and domain name
    base64_part, domain_name = encoded_string.split('.', 1)

    # Step 2: Convert the base64 string back to bytes
    xor_result = base64_to_bin(base64_part)

    # Step 3: Hash the domain name to get the original domain hash bytes (up to 18 bytes)
    domain_bytes = domain_hash(domain_name)

    # Step 4: XOR the decoded bytes with the domain hash bytes to retrieve the original IP:Port bytes
    ip_port_bytes = xor_bytes(xor_result, domain_bytes)

    # Step 5: Convert the IP:Port bytes back to human-readable form
    ip_port = bin_to_ip_port(ip_port_bytes)

    print(f"Decoded IP:Port: {ip_port}")

# Function to hash the domain name (Step 1 in encoding)
def domain_hash(domain_name):
    sha1_hash = hashlib.sha1(domain_name.encode()).digest()
    truncated_bytes = sha1_hash[:18]  # 18 bytes for IPv6 + Port
    return truncated_bytes

# Function to decode base64 string to binary data, considering missing padding
def base64_to_bin(base64_string):
    # Add missing padding if necessary
    padded_base64_string = base64_string + '=' * ((4 - len(base64_string) % 4) % 4)
    return base64.b64decode(padded_base64_string)

# Function to XOR two byte sequences
def xor_bytes(bytes1, bytes2):
    return bytes(a ^ b for a, b in zip(bytes1, bytes2))

# Function to convert the binary data back to IP:Port format
def bin_to_ip_port(byte_data):
    if len(byte_data) == 6:  # IPv4
        ip_bytes = byte_data[:4]
        port_bytes = byte_data[4:6]
        ip = socket.inet_ntop(socket.AF_INET, ip_bytes)
    elif len(byte_data) == 18:  # IPv6
        ip_bytes = byte_data[:16]
        port_bytes = byte_data[16:18]
        ip = socket.inet_ntop(socket.AF_INET6, ip_bytes)
    else:
        raise ValueError("Unexpected length of byte_data. It should be 6 bytes for IPv4 or 18 bytes for IPv6.")

    port = int.from_bytes(port_bytes, byteorder='big')
    return f"{ip}:{port}"

if __name__ == "__main__":
    main()

