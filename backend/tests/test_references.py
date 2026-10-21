import ast
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from app.runner.references import load_pack
from app.runner.docker import DockerRunner


def test_pack_covers_exact_top_50_with_standalone_sources():
    root=Path(__file__).resolve().parents[2]
    source=json.loads((root/'vendor/algoTop-main/public/data/codetop.json').read_text(encoding='utf-8'))
    top={str(row['questionId']) for row in source['indexes']['overall'][:50]}
    pack=load_pack()
    assert set(pack)==top
    for entry in pack.values():
        assert len(entry['cases'])>=3
        assert entry['input_description'] and entry['output_description'] and entry['explanation'] and entry['complexity']
        ast.parse(entry['source_code'])
        assert '__name__' in entry['source_code']
        assert all(case['expected_stdout'] is not None for case in entry['cases'])


@pytest.mark.skipif(os.environ.get('CODETOP_REFERENCE_TESTS')!='1',reason='Set CODETOP_REFERENCE_TESTS=1 to validate all references in Docker')
def test_all_reference_programs_in_docker(tmp_path):
    from hashlib import sha256
    evidence=[]
    runner=DockerRunner(tmp_path)
    for key,entry in load_pack().items():
        result=runner.execute(str(uuid4()),entry['source_code'],entry['cases'])
        assert all(case['status']=='passed' for case in result['results']), (entry['display_id'], result)
        evidence.append({'source_record_id':key,'display_id':entry['display_id'],'source_sha256':sha256(entry['source_code'].encode()).hexdigest(),'tests_passed':len(entry['cases']),'python_version':result['python_version']})
    (tmp_path/'reference-validation.json').write_text(json.dumps({'image_ref':runner.image_ref,'references':evidence},ensure_ascii=False,indent=2),encoding='utf-8')
