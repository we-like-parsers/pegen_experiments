import pathlib
import shutil
import tokenize

import distutils.log
from distutils.core import Distribution, Extension
from distutils.command.clean import clean  # type: ignore
from distutils.command.build_ext import build_ext  # type: ignore

from pegen.c_generator import CParserGenerator
from pegen.tokenizer import Tokenizer
from pegen.tokenizer import grammar_tokenizer
from pegen.grammar import GrammarParser

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


def build_parser(
    grammar_file,
    output_file,
    compile_extension=False,
    verbose_tokenizer=False,
    verbose_parser=False,
):
    """[summary]

    Args:
        grammar_file ([type]): [description]
        output_file ([type]): [description]
        compile_extension (bool, optional): [description]. Defaults to False.

    Raises:
        parser.make_syntax_error: [description]

    Returns:
        [type]: [description]
    """
    with open(grammar_file) as file:
        tokenizer = Tokenizer(
            grammar_tokenizer(tokenize.generate_tokens(file.readline)),
            verbose=verbose_tokenizer,
        )
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        rules = parser.start()

        if not rules:
            raise parser.make_syntax_error(grammar_file)

    with open(output_file, "w") as file:
        gen: ParserGenerator
        if output_file.endswith(".c"):
            gen = CParserGenerator(rules.rules, file)
        elif output_file.endswith(".py"):
            gen = PythonParserGenerator(rules.rules, file)
        else:
            raise Exception("Your output file must either be a .c or .py file")
        gen.generate(grammar_file)

    if compile_extension:
        compile_c_extension(output_file)

    return rules, parser, tokenizer, gen
