"""Regression checks for completion vs score eligibility in the published board."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest


def test_completion_display_and_participating_product():
    node=shutil.which('node')
    if not node:pytest.skip('Node required for static leaderboard behavior check')
    html=Path('space/index.html').read_text()
    js=html.split('<script>')[1].split('</script>')[0]
    checks=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const data=JSON.parse(fs.readFileSync('results/leaderboard.json','utf8'));
const context={document:{getElementById:()=>({}),querySelectorAll:()=>[]},fetch:()=>new Promise(()=>{})};
vm.createContext(context);vm.runInContext(JSON.parse(process.argv[1]),context);
const llama=data.models.find(m=>m.id==='llama-guard-3-1b');
const a=context.view(llama,'full');
assert.equal(a.status,'Completed');assert.equal(a.score,0);assert.equal(a.recall,0);
assert(a.note.includes('480/480 valid'));assert(a.note.includes('All predictions safe'));
assert.equal(a.ci,'Not computed');
const nvidia=data.models.find(m=>m.id==='nemotron-safety-8b-v3');
const b=context.view(nvidia,'full');
assert(b.status.includes('1 invalid/error'));assert.equal(b.score,null);
assert(b.note.includes('479/480 valid'));assert(b.note.includes('output limit'));
assert(b.scoreReason.includes('Full requires'));assert.equal(b.coverage,479/480);
const own=data.models.find(m=>m.id==='openguardrails');
assert.equal(own.model,'OpenGuardrails');assert.equal(own.completion.valid,480);
assert.equal(own.full_index,92.91666666666667);
assert(!data.models.some(m=>/Text-4B-0124|Xiangxin/i.test(m.model)));
assert.equal(new Set(data.models.map(m=>m.id)).size,data.models.length);
assert.equal(data.models.length,8);
'''
    subprocess.run([node,'-e',checks,json.dumps(js)],check=True,capture_output=True,text=True)
    assert 'Public recall' in html and 'Run status' in html


def test_openguardrails_receipts_preserve_numerical_outputs():
    p=Path('results/public/openguardrails')
    cfg=json.loads((p/'config.json').read_text())
    assert cfg['model']=='OpenGuardrails' and 'api_model' not in cfg
    assert cfg['deployment']['image_id']==cfg['revision']
    rows=[json.loads(l) for l in (p/'results.jsonl').read_text().splitlines()]
    assert len(rows)==192
    for row in rows:
        raw=json.loads(row['raw'])
        assert raw['model']=='OpenGuardrails' and row['backend_alias_redacted'] is True
        assert row['unsafe']==(raw['answers']['unsafe']['noul']>=.5)
