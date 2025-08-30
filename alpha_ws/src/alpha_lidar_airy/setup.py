from setuptools import setup

package_name = 'alpha_lidar_airy'

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
    description='RoboSense AIRY LiDAR support: op-mode HTTP service + organized cloud reorder (skeleton).',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mode_service_node = alpha_lidar_airy.mode_service_node:main',
            'reorder_node = alpha_lidar_airy.reorder_node:main',
        ],
    },
)

