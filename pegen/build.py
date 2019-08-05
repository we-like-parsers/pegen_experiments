import pathlib
import shutil

import distutils.log
from distutils.core import Distribution, Extension
from distutils.command.clean import clean # type: ignore
from distutils.command.build_ext import build_ext # type: ignore

MOD_DIR = pathlib.Path(__file__)


def compile_c_extension(generated_source_path, build_dir=None, verbose=False):
    """Compile the generated source for a parser generator into an extension module.

    The extension module will be generated in the same directory as the provided path
    for the generated source, with the same basename (in addition to extension module
    metadata). For example, for the source mydir/parser.c the generated extension
    in a darwin system with python 3.8 will be mydir/parser.cpython-38-darwin.so.

    If *build_dir* is provided, that path will be used as the temporary build directory
    of distutils (this is useful in case you want to use a temporary directory).
    """
    if verbose:
        distutils.log.set_verbosity(distutils.log.DEBUG)

    source_file_path = pathlib.Path(generated_source_path)
    extension_name = source_file_path.stem
    extension = [Extension(extension_name,
                           sources=[str(MOD_DIR.parent / "pegen.c"), generated_source_path],
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
