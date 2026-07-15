import os
import re

pages = [
    'login.html', 'dashboard.html', 'live-calls.html',
    'analytics.html', 'knowledge.html', 'profile.html', 'settings.html'
]

base = r'a:\VoxAgentAI\frontend'
missing = []

for page in pages:
    path = os.path.join(base, page)
    if not os.path.exists(path):
        missing.append('MISSING PAGE: ' + page)
        continue
    content = open(path, encoding='utf-8', errors='ignore').read()
    refs = re.findall(r'(?:src|href)=["\']((js/|css/|assets/)[^"\'?#]+)', content)
    for ref_tuple in refs:
        ref = ref_tuple[0]
        full = os.path.join(base, ref.replace('/', os.sep))
        if not os.path.exists(full):
            missing.append(page + ' -> MISSING: ' + ref)

if missing:
    for m in missing:
        print(m)
else:
    print('ALL FILES PRESENT')
