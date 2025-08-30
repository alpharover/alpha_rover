from setuptools import setup

package_name = 'alpha_recorder'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'PyYAML'],
    zip_safe=True,
    maintainer='Alpha SW',
    maintainer_email='devnull@example.com',
    description='Ring buffer and triggered recording for ALPHA.',
    license='Proprietary',
    entry_points={
        'console_scripts': [
            'ring_recorder = alpha_recorder.ring_recorder_node:main',
        ],
    },
)

