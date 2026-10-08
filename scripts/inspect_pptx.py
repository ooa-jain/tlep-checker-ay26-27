import sys
sys.stdout.reconfigure(encoding='utf-8')
import zipfile, xml.etree.ElementTree as ET

try:
    with zipfile.ZipFile(r'C:\Users\jljga\Downloads\DIAC_DPAC_BoS_Process_TLEP_Format.pptx') as z:
        slides = [n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        print('Slides found:', len(slides))
        for s in sorted(slides):
            root = ET.fromstring(z.read(s))
            texts = [node.text for node in root.iter() if node.text and node.text.strip()]
            print(f'=== {s} ===')
            print('\n'.join(texts))
except Exception as e:
    print('Error:', e)
