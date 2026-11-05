"""Check two safe exports through the packaged app's real HTTP endpoints."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
bundle = ROOT / 'dist/VideoCompressAutocutSafe.app'
helper = bundle / 'Contents/Resources/cinematic_blur'
# Bundle signing changes Mach-O signature bytes; compare executable text only.
def executable_text(path):
    return subprocess.check_output(['otool', '-s', '__TEXT', '__text', str(path)], text=True).splitlines()[1:]
assert executable_text(helper) == executable_text(ROOT/'cinematic_blur')
with tempfile.TemporaryDirectory(prefix='packaged-safe-') as tmp:
    root = Path(tmp)
    source = root/'synthetic.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','0.6','-c:v','libx264','-threads','2','-c:a','aac',str(source)],check=True)
    env = dict(os.environ, VIDEO_MCP_RUNTIME_DIR=str(root/'runtime'), VIDEO_AI_CONFIG=str(root/'models.json'))
    with open(root/'app.log','w') as log:
        p = subprocess.Popen([str(bundle/'Contents/MacOS/VideoCompressAutocutSafe')],env=env,stdout=log,stderr=log)
        try:
            for _ in range(600):
                descriptors = list((root/'runtime').glob('*.json'))
                if descriptors:break
                if p.poll() is not None:raise RuntimeError((root/'app.log').read_text()[-1000:])
                time.sleep(.1)
            else:raise RuntimeError('Packaged app startup timeout')
            descriptor = json.loads(descriptors[0].read_text())
            url = f"http://127.0.0.1:{descriptor['port']}"
            def post(endpoint, body=None, raw=None):
                headers={'Origin':url,'Content-Type':'application/json'}
                if raw is not None: headers.update({'X-File-Name':'synthetic.mp4','Content-Type':'application/octet-stream'})
                req=urllib.request.Request(url+endpoint,data=raw if raw is not None else json.dumps(body).encode(),headers=headers)
                with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
            for n in range(2):
                task=post('/api/upload',raw=source.read_bytes())
                post('/api/process',dict(id=task['id'],mode='none',enable_bokeh=True,then_compress=True,target_mb=1,hardware_encode=bool(n)))
                for _ in range(600):
                    with urllib.request.urlopen(url+'/api/progress?id='+task['id'],timeout=5) as response: state=json.load(response)
                    if state['status'] in ('completed','error'):break
                    time.sleep(.2)
                assert state['status']=='completed',state
                assert state['result']['width']==320
                print('PASS packaged export',n+1,'hardware_encode',bool(n),flush=True)
        finally:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
