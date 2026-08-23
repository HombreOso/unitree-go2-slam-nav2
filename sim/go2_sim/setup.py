import os
from glob import glob

from setuptools import setup

package_name = 'go2_sim'


def data_files_for(subdir):
    """Install every file under `subdir` into the package share directory."""
    out = []
    for root, _dirs, files in os.walk(subdir):
        if not files:
            continue
        dest = os.path.join('share', package_name, root)
        out.append((dest, [os.path.join(root, f) for f in files]))
    return out


setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ] + data_files_for('worlds') + data_files_for('urdf') + data_files_for('config'),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Arthur Emig',
    maintainer_email='arthur.e.emig@gmail.com',
    description='Go2 construction-site simulation for the VLM/LLM safety inspection pipeline.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'waypoint_mission = go2_sim.waypoint_mission:main',
            'frame_capture = go2_sim.frame_capture:main',
            'cmd_vel_bridge = go2_sim.cmd_vel_bridge:main',
        ],
    },
)
