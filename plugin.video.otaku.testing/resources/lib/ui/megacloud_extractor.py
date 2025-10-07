"""
MegaCloud/VidCloud video source extractor
Ported from: https://github.com/Goldenfreddy0703/mega-embed-2
"""
import re
import json
import base64
import urllib.parse
from resources.lib.ui import client


def _get_decryption_keys():
    """Fetch decryption keys from GitHub (small file, no caching needed)"""
    keys_url = "https://raw.githubusercontent.com/yogesh-hacker/MegacloudKeys/refs/heads/main/keys.json"
    user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"

    try:
        keys_response = client.get(keys_url, headers={"User-Agent": user_agent}, timeout=10)
        if keys_response and keys_response.text:
            return keys_response.json()
    except Exception as e:
        from resources.lib.ui import control
        control.log(f"Failed to fetch decryption keys: {str(e)}")

    return None


class MegacloudDecryptor:
    """Decrypts encrypted video sources from MegaCloud/VidCloud"""

    def __init__(self):
        self.DEFAULT_CHARSET = [chr(i) for i in range(32, 127)]  # ASCII 32-126 (95 chars)

    def keygen2(self, megacloud_key, client_key):
        """Generate decryption key from megacloud and client keys"""
        temp_key = megacloud_key + client_key

        # Numeric hash
        hash_val = 0
        keygen_hash_mult_val = 31
        for char in temp_key:
            hash_val = ord(char) + hash_val * keygen_hash_mult_val + (hash_val << 7) - hash_val

        # Get absolute value
        hash_val = abs(hash_val)
        l_hash = hash_val % 0x7FFFFFFFFFFFFFFF  # Limit to 64 bits

        # Apply XOR
        keygen_xor_val = 247
        temp_key = ''.join(chr(ord(c) ^ keygen_xor_val) for c in temp_key)

        # Circular shift
        keygen_shift_val = 5
        pivot = l_hash % len(temp_key) + keygen_shift_val
        temp_key = temp_key[pivot:] + temp_key[:pivot]

        # Leaf in values
        leaf_str = client_key[::-1]  # Reverse
        return_key = ""
        max_len = max(len(temp_key), len(leaf_str))
        for i in range(max_len):
            return_key += (temp_key[i] if i < len(temp_key) else "") + (leaf_str[i] if i < len(leaf_str) else "")

        # Limit the length of the key
        return_key = return_key[:96 + l_hash % 33]  # Clamps between 96 and 128

        # Normalize to ASCII values
        return_key = ''.join(chr(ord(c) % 95 + 32) for c in return_key)

        return return_key

    def columnar_cipher2(self, src, ikey):
        """Columnar transposition cipher"""
        column_count = len(ikey)
        row_count = (len(src) + column_count - 1) // column_count  # Ceiling division

        cipher_array = [[' ' for _ in range(column_count)] for _ in range(row_count)]

        # Create sorted key map
        key_map = [{"char": char, "idx": idx} for idx, char in enumerate(ikey)]
        sorted_map = sorted(key_map, key=lambda x: ord(x["char"]))

        # Fill cipher array
        src_index = 0
        for item in sorted_map:
            index = item["idx"]
            for i in range(row_count):
                if src_index < len(src):
                    cipher_array[i][index] = src[src_index]
                    src_index += 1

        # Collapse the array
        return_str = ""
        for row in cipher_array:
            for char in row:
                return_str += char

        return return_str

    def seed_shuffle2(self, character_array, ikey):
        """Deterministic shuffle based on seed from key"""
        hash_val = 0
        for char in ikey:
            hash_val = (hash_val * 31 + ord(char)) & 0xFFFFFFFF

        shuffle_num = hash_val

        def pseudo_rand(arg):
            nonlocal shuffle_num
            shuffle_num = (shuffle_num * 1103515245 + 12345) & 0x7FFFFFFF
            return shuffle_num % arg

        ret_str = list(character_array)
        for i in range(len(ret_str) - 1, 0, -1):
            swap_index = pseudo_rand(i + 1)
            ret_str[i], ret_str[swap_index] = ret_str[swap_index], ret_str[i]

        return ret_str

    def decrypt(self, src, client_key, megacloud_key):
        """Decrypt encrypted source string"""
        layers = 3
        gen_key = self.keygen2(megacloud_key, client_key)
        dec_src = base64.b64decode(src).decode('utf-8')
        char_array = self.DEFAULT_CHARSET

        def reverse_layer(iteration):
            nonlocal dec_src
            layer_key = gen_key + str(iteration)

            # Seed hash
            hash_val = 0
            for char in layer_key:
                hash_val = (hash_val * 31 + ord(char)) & 0xFFFFFFFF

            seed = hash_val

            def seed_rand(arg):
                nonlocal seed
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                return seed % arg

            # Seed shift
            dec_src_list = list(dec_src)
            for i in range(len(dec_src_list)):
                char = dec_src_list[i]
                try:
                    c_array_index = char_array.index(char)
                    rand_num = seed_rand(95)
                    new_char_index = (c_array_index - rand_num + 95) % 95
                    dec_src_list[i] = char_array[new_char_index]
                except ValueError:
                    pass  # Char not in array, keep as is

            dec_src = ''.join(dec_src_list)

            # Run columnar cipher
            dec_src = self.columnar_cipher2(dec_src, layer_key)

            # Run seeded shuffle
            sub_values = self.seed_shuffle2(char_array, layer_key)
            char_map = {sub_values[i]: char_array[i] for i in range(len(sub_values))}

            # Substitute characters
            dec_src = ''.join(char_map.get(char, char) for char in dec_src)

        # Reverse all layers
        for i in range(layers, 0, -1):
            reverse_layer(i)

        # Extract actual data (first 4 chars are length)
        try:
            data_len = int(dec_src[:4])
            return dec_src[4:4 + data_len]
        except (ValueError, IndexError):
            return dec_src


def extract_megacloud_sources(embed_url, referer="https://hianime.to/"):
    """
    Extract video sources from MegaCloud/VidCloud embed URLs

    Args:
        embed_url: The embed URL (e.g., https://megacloud.blog/embed-2/v3/e-1/xxxxx?k=1)
        referer: The referer URL to use in requests

    Returns:
        dict with keys: sources (list), tracks (list), intro (dict), outro (dict)
        Returns None on failure
    """
    try:
        user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"

        # Parse the embed URL
        url_obj = urllib.parse.urlparse(embed_url)
        domain = url_obj.netloc
        parts = url_obj.path.split("/")
        xrax = parts[-1].split('?')[0]  # Remove query params
        path = '/'.join(parts[:-1])
        get_sources_base = f"https://{domain}{path}/getSources?id="

        # Step 1: Fetch embed page to extract nonce
        headers = {
            "User-Agent": user_agent,
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest",
        }

        response = client.get(embed_url, headers=headers, timeout=8)
        if not response or not response.text:
            return None

        html = response.text

        # Extract nonce (48-char key or 3x16-char keys concatenated)
        match = re.search(r'\b[a-zA-Z0-9]{48}\b', html)
        if not match:
            # Try 3x16 pattern
            match = re.search(r'\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b', html)
            if match:
                nonce = match.group(1) + match.group(2) + match.group(3)
            else:
                return None
        else:
            nonce = match.group(0)

        # Step 2: Fetch sources with nonce
        get_sources_url = f"{get_sources_base}{xrax}&_k={nonce}"
        response = client.get(get_sources_url, headers=headers, timeout=8)
        if not response or not response.text:
            return None

        data = response.json()

        # Step 3: Decrypt if encrypted
        if data.get('encrypted'):
            # Get decryption keys from GitHub
            keys = _get_decryption_keys()
            if not keys:
                return None

            key = keys.get("vidstr")
            if not key:
                return None

            # Decrypt sources
            decryptor = MegacloudDecryptor()
            decrypted = decryptor.decrypt(data['sources'], nonce, key)

            try:
                data['sources'] = json.loads(decrypted)
            except json.JSONDecodeError:
                data['sources'] = [{"file": ""}]

        return data

    except Exception as e:
        # Log error but don't crash
        from resources.lib.ui import control
        control.log(f"MegaCloud extractor error: {str(e)}")
        return None
