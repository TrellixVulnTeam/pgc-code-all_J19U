
import argparse
import os


def folder_structure(input_dir, out_file, ignore_ext, ignore_dir):
    with open(out_file, 'w') as of:
        for root, dirs, files in os.walk(INPUT):
            dirs[:] = [d for d in dirs if d not in ignore_dir]
            level = root.replace(INPUT, '').count(os.sep)
            indent= ' ' * 4 * level
            of.write('{}{}/\n'.format(indent, os.path.basename(root)))
            print('{}{}/'.format(indent, os.path.basename(root)))
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                ext = f.split('.')[-1]
                if ext not in ignore_ext:
                    of.write('{}{}\n'.format(subindent, f))
                    print('{}{}'.format(subindent, f))
        

if __name__ == '__main__':
    argdef = {'ignore_ext': ['ini', 'bak', 'pyc', ],
              'ignore_dir': ['.git', 'ignore',
                             '.spyproject',
                             '__pycache__',
                             '.pylint.d']}

    parser = argparse.ArgumentParser()

    parser.add_argument('--input_directory',
                        type=os.path.abspath,
                        default=os.getcwd(),
                        help='Path to directory to parse. Defaults to cwd')
    parser.add_argument('--out_file',
                        type=os.path.abspath,
                        help='''Path to text file to write out.
                                Defaults to {cwd}\{directory_name}_folder_structure.txt''')
    parser.add_argument('--ignore_ext',
                        nargs='+',
                        default=argdef['ignore_ext'],
                        help='Extensions to ignore.')
    parser.add_argument('--ignore_dir',
                        nargs='+',
                        default=argdef['ignore_dir'],
                        help='Directories to ignore.')

    args = parser.parse_args()

    INPUT = args.input_directory
    OUTFILE = args.out_file
    IGNORE_EXT = args.ignore_ext
    IGNORE_DIR = args.ignore_dir

    if not OUTFILE:
        OUTFILE = '{}_folder_structure.txt'.format(os.path.basename(INPUT))
    
    folder_structure(INPUT, OUTFILE, ignore_ext=IGNORE_EXT, ignore_dir=IGNORE_DIR)
