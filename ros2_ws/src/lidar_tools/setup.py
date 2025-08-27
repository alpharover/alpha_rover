from setuptools import setup

package_name = 'lidar_tools'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='alpha_orin',
    maintainer_email='alpha_orin@example.com',
    description='LiDAR point cloud utility nodes',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pc_repack = lidar_tools.pc_repack:main',
        ],
    },
)

