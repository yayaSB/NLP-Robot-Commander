from glob import glob
from setuptools import find_packages, setup

package_name = "nlp_robot_commander"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=("test",)),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    maintainer="Étudiant HESTIM",
    maintainer_email="student@example.com",
    description="Commande d'un robot Nav2 par intentions en langage naturel.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "nlp_commander = nlp_robot_commander.nlp_commander_node:main",
            "terminal_client = nlp_robot_commander.terminal_client:main",
            "microphone_client = nlp_robot_commander.microphone_client:main",
        ],
    },
)

