from setuptools import setup

package_name = 'alpha_observability'

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
    description='SLO metrics and diagnostic publishers for ALPHA (skeleton).',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'slo_publisher = alpha_observability.slo_publisher:main',
        ],
    },
)

