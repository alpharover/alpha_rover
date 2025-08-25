from setuptools import setup

package_name = 'oak_temp_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/oak_temp_bridge.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='alpha_orin',
    maintainer_email='alpha_orin@example.com',
    description='Extracts OAK device temperatures from diagnostics and republishes as sensor_msgs/Temperature',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'oak_temp_bridge = oak_temp_bridge.bridge_node:main',
        ],
    },
)

