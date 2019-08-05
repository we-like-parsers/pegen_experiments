import pathlib
import shutil

from distutils.core import Distribution, Extension
from distutils.command.clean import clean
from distutils.command.build_ext import build_ext

MOD_DIR = pathlib.Path(__file__)


def compile_c_extension(output, build_dir=None):
    source_file_path = pathlib.Path(output)
    extension_name = source_file_path.stem
    extension = [Extension(extension_name,
                           sources=[str(MOD_DIR.parent / "pegen.c"), output],
                           include_dirs=[str(MOD_DIR.parent)],
                           extra_compile_args=[], )]
    dist = Distribution({'name': extension_name, 'ext_modules': extension})
    cmd = build_ext(dist)
    cmd.inplace = True
    if build_dir:
        cmd.build_temp = build_dir
    cmd.ensure_finalized()
    cmd.run()

    extension_path = source_file_path.parent / cmd.get_ext_filename(extension_name)
    shutil.move(cmd.get_ext_fullpath(extension_name), extension_path)

    cmd = clean(dist)
    cmd.finalize_options()
    cmd.run()

    return extension_path
