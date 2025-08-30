from setuptools import setup

package_name = 'alpha_calibration_tools'

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
    description='Calibration tools and TF preflight check (skeleton).',
    license='Proprietary',
    entry_points={
        'console_scripts': [
            'tf_ok = alpha_calibration_tools.tf_ok_node:main',
        ],
    },
)

