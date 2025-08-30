from setuptools import setup

package_name = 'alpha_comms'

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
    description='Comms manager and degrade policy executor (skeleton).',
    license='Proprietary',
    entry_points={
        'console_scripts': [
            'degrade_manager = alpha_comms.degrade_manager_node:main',
            'video_budget_applier = alpha_comms.video_budget_applier_node:main',
            'video_controller = alpha_comms.video_controller_node:main',
        ],
    },
)
