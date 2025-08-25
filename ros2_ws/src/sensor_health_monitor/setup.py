from setuptools import setup

package_name = 'sensor_health_monitor'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/thermals.launch.py']),
        ('share/' + package_name + '/config', ['config/thermals.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='alpha_orin',
    maintainer_email='alpha_orin@example.com',
    description='ROS 2 diagnostics publisher for Jetson thermals',
    license='BSD-3-Clause',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'jetson_thermals = sensor_health_monitor.jetson_thermals_node:main',
        ],
    },
)

