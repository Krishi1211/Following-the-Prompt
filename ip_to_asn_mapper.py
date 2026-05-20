import subprocess
import re

def extract_ips_from_traceroute(traceroute_text):
    """
    Extracts IP addresses from raw traceroute output.
    """
    ips = []
    # Regex to find standard IPv4 addresses
    ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    
    for line in traceroute_text.splitlines():
        matches = ip_pattern.findall(line)
        if matches:
            # Often traceroute lines look like: 
            # 1  router.local (192.168.1.1)  1.000 ms
            # We want the IPs found
            ips.extend(matches)
    
    # Remove duplicates but preserve order
    return list(dict.fromkeys(ips))

def ip_to_asn(ip):
    """
    Queries Team Cymru's DNS service to find the ASN for an IP.
    Returns (ASN, BGP Prefix, Organization)
    """
    try:
        # Reverse IP: 1.2.3.4 -> 4.3.2.1
        reversed_ip = '.'.join(ip.split('.')[::-1])
        query = f"{reversed_ip}.origin.asn.cymru.com"
        
        # Run dig command
        result = subprocess.run(['dig', '+short', 'TXT', query], capture_output=True, text=True)
        
        output = result.stdout.strip().strip('"')
        if output:
            # Output format: "ASN | BGP Prefix | CC | Registry | Date"
            parts = [p.strip() for p in output.split('|')]
            asn = parts[0]
            prefix = parts[1] if len(parts) > 1 else ""
            
            # Optionally, get the ASN organization name
            org_query = f"AS{asn}.asn.cymru.com"
            org_result = subprocess.run(['dig', '+short', 'TXT', org_query], capture_output=True, text=True)
            org_output = org_result.stdout.strip().strip('"')
            
            org_name = ""
            if org_output:
                # Format: "ASN | CC | Registry | Date | Organization Name"
                org_parts = [p.strip() for p in org_output.split('|')]
                if len(org_parts) >= 5:
                    org_name = org_parts[4]
                    
            return asn, prefix, org_name
            
        return "Unknown", "", ""
    except Exception as e:
        return "Error", str(e), ""

if __name__ == "__main__":
    test_ip = "8.8.8.8"
    print(f"Testing ASN lookup for {test_ip}...")
    asn, prefix, org = ip_to_asn(test_ip)
    print(f"IP: {test_ip}")
    print(f"ASN: {asn}")
    print(f"Prefix: {prefix}")
    print(f"Organization: {org}")
