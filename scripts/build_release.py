"""Build the installable legacy Blender add-on ZIP without repository or development files."""
import argparse
import ast
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
# Keep the installed module name stable, including when the checkout directory differs.
PACKAGE_NAME = 'Facial-Shapekeys-Plus'
ROOT_FILES = ('__init__.py', 'memory.py', 'properties.py', 'join_support.py', 'config.ini', 'LICENSE.md')
MODULE_DIRECTORIES = ('core', 'operators', 'menus', 'panels')


def read_metadata(root=ROOT):
    module = ast.parse((root / '__init__.py').read_bytes())
    metadata = {}
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, 'id', '') in ('bl_info', 'bl_info_en_US', 'bl_info_ja_JP'):
                    metadata[target.id] = ast.literal_eval(node.value)
    info = metadata['bl_info']
    version = info['version']
    if (not isinstance(version, tuple) or len(version) != 3
            or any(type(number) is not int or number < 0 for number in version)):
        raise ValueError('bl_info.version must contain three nonnegative integers')
    for name, translated in metadata.items():
        for field in ('name', 'author', 'version'):
            if translated[field] != info[field]:
                raise ValueError(f'{name}.{field} differs from bl_info.{field}')
    return info


def build_archive(output, tag=None, root=ROOT):
    info = read_metadata(root)
    expected_tag = 'v' + '.'.join(str(number) for number in info['version'])
    if tag is not None and tag != expected_tag:
        raise ValueError(f'Release tag {tag!r} does not match add-on version {expected_tag}')

    files = [root / name for name in ROOT_FILES]
    for directory in MODULE_DIRECTORIES:
        files.extend(sorted((root / directory).glob('*.py')))
    payloads = {PACKAGE_NAME + '/' + path.relative_to(root).as_posix(): path.read_bytes()
                for path in files}

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in payloads.items():
            # Normalize line endings so Windows and Linux builds contain identical source.
            content = content.replace(b'\r\n', b'\n')
            member = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.create_system = 3
            member.external_attr = 0o100644 << 16
            archive.writestr(member, content, compress_type=ZIP_DEFLATED, compresslevel=9)

    with ZipFile(output) as archive:
        if archive.testzip() is not None or archive.namelist() != list(payloads):
            raise ValueError('Built ZIP failed its integrity check')
        for name, content in payloads.items():
            if archive.read(name) != content.replace(b'\r\n', b'\n'):
                raise ValueError(f'Packaged content differs from source: {name}')
    return len(payloads)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', help='Require a release tag matching bl_info.version, e.g. v2.2.4')
    parser.add_argument('--output', type=Path, default=ROOT / (PACKAGE_NAME + '.zip'))
    args = parser.parse_args()
    try:
        count = build_archive(args.output, tag=args.tag)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))
    print(f'Built {args.output} ({count} files)')
    print(f'SHA256: {sha256(args.output.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
