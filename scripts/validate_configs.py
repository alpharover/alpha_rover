#!/usr/bin/env python3
import sys
import json
from pathlib import Path

import yaml
from jsonschema import validate as jsonschema_validate, ValidationError


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    cfg_dir = repo / 'alpha_configs'
    schema_dir = cfg_dir / 'schemas'
    errors = []
    for yml in sorted(cfg_dir.glob('*.yaml')):
        key = yml.stem
        schema_path = schema_dir / f'{key}.schema.json'
        if not schema_path.exists():
            continue
        try:
            data = yaml.safe_load(yml.read_text())
            schema = json.loads(schema_path.read_text())
            jsonschema_validate(instance=data, schema=schema)
            print(f'[OK] {yml.name}')
        except ValidationError as ve:
            errors.append(f'[FAIL] {yml.name}: {ve.message}')
        except Exception as e:
            errors.append(f'[ERROR] {yml.name}: {e}')
    if errors:
        print('\n'.join(errors))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

