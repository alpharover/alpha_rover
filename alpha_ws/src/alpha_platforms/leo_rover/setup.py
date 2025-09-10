from setuptools import setup
from pathlib import Path

package_name = 'alpha_platforms_leo_rover'

def files_in(dir_rel: str):
    base = Path('share') / package_name / dir_rel
    src = Path(dir_rel)
    files = [str(p) for p in src.glob('**/*') if p.is_file()]
    return [(str(base), files)] if files else []

data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
]
data_files += files_in('launch')
data_files += files_in('config')
data_files += files_in('urdf')

# Explicit packages to avoid namespace/distribution resolution issues
packages = [
    'alpha_platforms',
    'alpha_platforms.leo_rover',
]

setup(
    name=package_name,
    version='0.1.0',
    packages=packages,
    package_dir={'alpha_platforms': 'src/alpha_platforms'},
    data_files=data_files,
    install_requires=['setuptools', 'PyYAML'],
    zip_safe=True,
    maintainer='ALPHA',
    maintainer_email='alpha@alpharover.org',
    description='ALPHA adapter for Leo Rover v1.x',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'leorover_adapter_node=alpha_platforms.leo_rover.adapter_node:main',
    ]},
)
