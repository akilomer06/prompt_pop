"""Validate checked-in hosting settings against the providers' current JSON schemas."""
import json
import os
from pathlib import Path
import subprocess
import httpx
import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
for name, schema_url, configuration in [
    ('Render', 'https://render.com/schema/render.yaml.json', yaml.safe_load((ROOT / 'render.yaml').read_text())),
    ('Vercel', 'https://openapi.vercel.sh/vercel.json', json.loads(subprocess.check_output(
        ['node', '--input-type=module', '-e', "import {config} from './frontend/vercel.ts'; console.log(JSON.stringify(config))"],
        cwd=ROOT, env={**os.environ, 'BACKEND_ORIGIN': 'https://api.example'}, text=True))),
]:
    response = httpx.get(schema_url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    schema = response.json()
    # Vercel's published schema uses draft-07 tuple schemas without declaring a dialect.
    validator = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
    errors = list(validator(schema).iter_errors(configuration))
    if errors:
        raise SystemExit('\n'.join(f'{name}: {list(error.path)}: {error.message}' for error in errors))
    print(f'{name}: configuration passes official JSON schema')
