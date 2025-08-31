from setuptools import setup
from glob import glob

package_name = 'alpha_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools', 'PyYAML', 'jsonschema'],
    zip_safe=True,
    maintainer='Alpha SW',
    maintainer_email='devnull@example.com',
    description='Startup sequencer and config manager for ALPHA.',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'config_manager = alpha_bringup.config_manager:main',
            'startup_sequencer = alpha_bringup.startup_sequencer:main',
            'lidar_ready_gate = alpha_bringup.lidar_ready_gate:main',
            'mapping_autostart = alpha_bringup.mapping_autostart:main',
        ],
    },
)
