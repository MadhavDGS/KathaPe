"""
Patches for common network issues in cloud hosting environments
"""
import socket
import functools

# Known Supabase IPs
SUPABASE_HOSTS = {
    'xhczvjwwmrvmcbwjxpxd.supabase.co': '143.198.222.201', # Use a real IP if you know it
}

# Override socket.getaddrinfo to handle DNS resolution for known hosts
original_getaddrinfo = socket.getaddrinfo

@functools.wraps(original_getaddrinfo)
def patched_getaddrinfo(host, port, *args, **kwargs):
    print(f"DNS lookup for: {host}:{port}")
    
    # Check if this is a known Supabase host
    if host in SUPABASE_HOSTS:
        # Use hardcoded IP for known Supabase domains
        print(f"Using hardcoded IP {SUPABASE_HOSTS[host]} for {host}")
        
        # Format result in the same way as getaddrinfo would
        # (family, socktype, proto, canonname, sockaddr)
        if ':' in SUPABASE_HOSTS[host]:  # IPv6
            return [(socket.AF_INET6, socket.SOCK_STREAM, 0, '', (SUPABASE_HOSTS[host], port, 0, 0))]
        else:  # IPv4
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, '', (SUPABASE_HOSTS[host], port))]
    
    # Fall back to original implementation for non-Supabase hosts
    return original_getaddrinfo(host, port, *args, **kwargs)

def apply_patches():
    """Apply all network patches"""
    # Replace the socket.getaddrinfo function with our patched version
    socket.getaddrinfo = patched_getaddrinfo
    print("Applied DNS resolution patches")

def remove_patches():
    """Remove all applied patches"""
    # Restore original getaddrinfo function
    socket.getaddrinfo = original_getaddrinfo
    print("Removed DNS resolution patches") 