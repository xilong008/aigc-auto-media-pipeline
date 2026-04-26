import json

def convert(ui_path, api_path):
    with open(ui_path, 'r') as f:
        ui = json.load(f)
    
    links = {}
    for l in ui.get('links', []):
        if not l: continue
        link_id = l[0]
        src_id = l[1]
        src_slot = l[2]
        links[link_id] = [str(src_id), src_slot]
        
    api = {}
    for node in ui['nodes']:
        node_id = str(node['id'])
        node_api = {
            "class_type": node['type'],
            "inputs": {}
        }
        
        # We need to reconstruct the widgets and inputs.
        # However, the mapping of widgets to inputs is complicated.
        # It's better to tell the user to export from ComfyUI UI,
        # OR we can just write the correct API workflow for LTX-Video.
