from setuptools import setup

package_name = 'alpha_mode_manager'

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
    maintainer='Alpha SW',
    maintainer_email='devnull@example.com',
    description='Hierarchical mode manager (skeleton); serves ModeSet and publishes ModeState.',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mode_manager = alpha_mode_manager.mode_manager_node:main',
        ],
    },
)

