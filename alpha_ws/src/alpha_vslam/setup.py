from setuptools import setup

package_name = 'alpha_vslam'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/isaac_visual_slam.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alpha SW',
    maintainer_email='devnull@example.com',
    description='Launch wrapper for Isaac ROS Visual SLAM',
    license='Proprietary',
    entry_points={
        'console_scripts': [],
    },
)

