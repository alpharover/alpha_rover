from pathlib import Path
import yaml


def test_mapping_yaml_loads():
    p = Path(__file__).parent.parent / 'config' / 'leo_rover.yaml'
    cfg = yaml.safe_load(p.read_text())
    assert 'mappings' in cfg and isinstance(cfg['mappings'], list)

