
from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension(
        "matching_engine",
        ["matching_engine.pyx"],
    )
]

setup(
    name="ChronosMatch",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    ),
)

