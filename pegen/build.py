import pathlib
import shutil
import tokenize

import distutils.log
from distutils.core import Distribution, Extension
from distutils.command.clean import clean  # type: ignore
from distutils.command.build_ext import build_ext  # type: ignore

from pegen.parser_generator import ParserGenerator
from pegen.python_generator import PythonParserGenerator
from pegen.c_generator import CParserGenerator
from pegen.tokenizer import Tokenizer
from pegen.tokenizer import grammar_tokenizer
from pegen.grammar_parser import GeneratedParser as GrammarParser

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
    extension = [
        Extension(
            extension_name,
            sources=[str(MOD_DIR.parent / "pegen.c"), generated_source_path],
            include_dirs=[str(MOD_DIR.parent)],
            extra_compile_args=[],
        )
    ]
    dist = Distribution({"name": extension_name, "ext_modules": extension})
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


def build_parser(grammar_file, verbose_tokenizer=False, verbose_parser=False):
    with open(grammar_file) as file:
        tokenizer = Tokenizer(
            grammar_tokenizer(tokenize.generate_tokens(file.readline)), verbose=verbose_tokenizer
        )
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        grammar = parser.start()

        if not grammar:
            raise parser.make_syntax_error(grammar_file)

    return grammar, parser, tokenizer


def build_generator(
    tokenizer, grammar, grammar_file, output_file, compile_extension=False, verbose_c_extension=False
):
    with open(output_file, "w") as file:
        gen: ParserGenerator
        if output_file.endswith(".c"):
            gen = CParserGenerator(grammar, file)
        elif output_file.endswith(".py"):
            gen = PythonParserGenerator(grammar, file)
        else:
            raise Exception("Your output file must either be a .c or .py file")
        gen.generate(grammar_file)

    if compile_extension and output_file.endswith(".c"):
        compile_c_extension(output_file, verbose=verbose_c_extension)

    return gen


def build_parser_and_generator(
    grammar_file,
    output_file,
    compile_extension=False,
    verbose_tokenizer=False,
    verbose_parser=False,
    verbose_c_extension=False,
):
    """Generate rules, parser, tokenizer, parser generator for a given grammar

    Args:
        grammar_file (string): Path for the grammar file
        output_file (string): Path for the output file
        compile_extension (bool, optional): Whether to compile the C extension.
          Defaults to False.
        verbose_tokenizer (bool, optional): Whether to display additional output
          when generating the tokenizer. Defaults to False.
        verbose_parser (bool, optional): Whether to display additional output
          when generating the parser. Defaults to False.
        verbose_c_extension (bool, optional): Whether to display additional
          output when compiling the C extension . Defaults to False.
    """
    grammar, parser, tokenizer = build_parser(grammar_file, verbose_tokenizer, verbose_parser)
    gen = build_generator(
        tokenizer, grammar, grammar_file, output_file, compile_extension, verbose_c_extension
    )

    return grammar, parser, tokenizer, gen
