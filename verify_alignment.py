import os
from lxml import etree

def verify_svg(filename):
    print(f"Verifying {filename}...")
    try:
        tree = etree.parse(filename)
        root = tree.getroot()
        
        # Namespace map if needed, but usually lxml handles it or we use local-name()
        # The file has xmlns="http://www.w3.org/2000/svg"
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Find all tex spans that are keys
        # We look for the pattern: key -> colon -> cc (dots)
        # Actually easier to iterate over all text/tspan elements and reconstruct lines
        # But let's just look for the specific structure we modified.
        
        # We want to find <tspan class="key">KEY</tspan> followed immediately by :<tspan class="cc">DOTS</tspan>
        # effectively checking the text content of the parent or siblings.
        
        # Let's iterate over the tspan elements with class='key'
        keys = root.findall(".//{http://www.w3.org/2000/svg}tspan[@class='key']")
        
        for key_elem in keys:
            key_text = key_elem.text
            # The next element (or text tail) should contain the colon and the dots
            # In the file: <tspan class="key">OS</tspan>:<tspan class="cc"> ... </tspan>
            # The colon is in the `tail` of the key_elem, or in a separate node?
            # XML: <tspan class="key">OS</tspan>:<tspan class="cc">
            # The colon ":" is the tail of key_elem.
            
            if key_elem.tail and ':' in key_elem.tail:
                # Find the next sibling which should be the dots
                dots_elem = key_elem.getnext()
                if dots_elem is not None and 'cc' in dots_elem.get('class', ''):
                    dots_text = dots_elem.text
                    
                    # Calculate total length
                    # Prefix is usually ". " (2 chars)
                    # But for some lines it might differ.
                    # Let's assume standard prefix ". " for all key-value lines we touched.
                    # Total = 2 + len(key_text) + 1 + len(dots_text)
                    
                    total_len = 2 + len(key_text) + 1 + len(dots_text)
                    print(f"Key: '{key_text}', Dots: '{dots_text}' (len {len(dots_text)}), Total: {total_len}")
                    
                    if total_len != 36:
                        print(f"  -> MISALIGNMENT! Expected 36, got {total_len}")
                    else:
                        print("  -> OK")
            else:
                 # It might be Languages.Programming
                 # <tspan class="key">Languages</tspan>.<tspan class="key">Programming</tspan>:
                 pass
                 
        # Special case for double keys like Languages.Programming
        # logic: find key, check if next is key.
        # This is getting complicated to parse perfectly with just loop.
        # Let's just Regex the file content.
        
    except Exception as e:
        print(f"Error parsing SVG: {e}")

def verify_file_regex(filename):
    import re
    print(f"Verifying {filename} with Regex...")
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern: . <key>:<dots>
    # or . <key>.<key>:<dots>
    
    # We want to capture the full line prefix up to value
    # Regex to capture: (prefix)(dots)
    # Prefix includes keys.
    
    # Look for lines containing class="cc">. </tspan> ... <tspan class="cc"> ...dots... </tspan>
    
    lines = content.split('\n')
    for line in lines:
        if '<tspan class="key">' in line and 'class="cc">' in line and '................' in line:
            # Extract plain text from the line (roughly) to count chars
            # Remove xml tags
            plain = re.sub(r'<[^>]+>', '', line)
            # The line usually has: ". Key: ..... Value"
            # We want length up to Value start.
            # Split by Value start?
            # Value is usually in <tspan class="value">
            
            if 'class="value"' in line:
                prefix_part = line.split('<tspan class="value"')[0]
                plain_prefix = re.sub(r'<[^>]+>', '', prefix_part)
                # plain_prefix usually includes the trailing space of dots: " ........................ "
                # And the leading space of the line?
                # The tspan for prefix ". " is <tspan ...>. </tspan>
                # The text is ". "
                
                # We need to be careful about spaces in the XML that aren't rendered.
                # However, the file has "text, tspan {white-space: pre;}" css.
                # So all spaces in text count.
                
                # Check length of plain_prefix
                # It might include indentation spaces?
                # The file has indentation.
                # But inside <tspan> content is what matters.
                # The indentation is outside tspans usually?
                # No, line 48: <tspan x="390" ...>. </tspan><tspan class="key">OS</tspan>...
                # All on one line? Yes.
                # So stripping tags gives the content.
                
                # Remove spaces from the START of the string if they are outside tags?
                # plain_prefix from "            <tspan..."
                # stripped of tags: "            . OS: ...."
                # We want to ignore the XML indentation.
                # The text starts at the first real character.
                
                stripped_prefix = plain_prefix.strip()
                # But wait, the first tspan content is ". ".
                # So if we strip, we might lose real spaces?
                # The structure is <tspan>. </tspan>
                # It's ". "
                
                # Let's just find the substring starting with ". "
                if ". " in plain_prefix:
                    start_idx = plain_prefix.find(". ")
                    relevant_part = plain_prefix[start_idx:]
                    print(f"Line content: '{relevant_part}' -> Len: {len(relevant_part)}")
                    if len(relevant_part) != 36:
                         print("  -> FAIL")
                    else:
                         print("  -> OK")

verify_file_regex('d:/Projects/git_readme/dark_mode.svg')
verify_file_regex('d:/Projects/git_readme/light_mode.svg')
