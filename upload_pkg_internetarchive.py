#!/usr/bin/env python

import sys
import os
import re
import xtarfile as tarfile
import traceback

import internetarchive as ia

import DB
# Source: http://stackoverflow.com/a/434328/953022
def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

class ArchiveUploader:
    DESCRIPTION = """{pkgdesc}

    This item contains old versions of the <a href="https://www.archlinux.org/packages/{pkgname}">Arch Linux package for {pkgname}</a>.
    Website of the upstream project: <a href="{url}">{url}</a>
    License: {license}
    See the <a href="https://wiki.archlinux.org/index.php/Arch_Linux_Archive">Arch Linux Archive documentation</a> for details.
    """

    def __init__(self, internetarchive = ia, db = None):
        self.ia = internetarchive
        self.db = db
        self.chunksize = 20
        if self.db is None:
            self.db = DB.DB('archive-uploader.sqlite')

    def clean_name(self, name):
        """Remove chars that are not allowed in an Internet Archive identifier: @.+
        Only alphanumerics, - and _ and allowed."""
        res = name.replace('@', '_')
        res = res.replace('+', '_')
        res = res.replace('.', '_')
        return res

    def extract_pkginfo(self, package):
        """Given a package (.tar.xz filename), extract and parse its .PKGINFO file as a dict"""
        with tarfile.open(package, mode='r') as tar:
            # Manual seeking to find .PKGINFO without having to uncompress the whole package
            while True:
                f = tar.next()
                if f.name == '.PKGINFO':
                    break
            pkginfo = tar.extractfile(f).readlines()
            # Parse .PKGINFO
            res = dict()
            for line in pkginfo:
                m = re.match(r'([^=]*) = (.*)', line.decode('utf8'))
                if m:
                    # TODO: support multi-valued attributes
                    key, value = m[1], m[2].strip()
                    res[key] = value
            return res

    def upload_pkg(self, identifier, pkgname, metadata, directory):
        """Upload all versions for package given by [directory]"""
        all_files = []
        returncode = 0
        for f in os.scandir(directory):
            filename = os.path.basename(f.path)
            if not self.db.exists(filename):
                all_files.append(f.path)
        if not all_files:
            return
        # ensure reproducible order for tests
        all_files.sort()
        # Get last package, to extract a description
        last_pkg = sorted(filter(lambda x: not x.endswith('.sig'), all_files))[-1]
        pkginfo = self.extract_pkginfo(last_pkg)
        pkgdesc = pkginfo['pkgdesc'] if 'pkgdesc' in pkginfo else ''
        if 'license' not in pkginfo:
            pkginfo['license'] = ''
        metadata['description'] = ArchiveUploader.DESCRIPTION.format(pkgname=pkgname, pkgdesc=pkgdesc, url=pkginfo['url'], license=pkginfo['license'])
        metadata['rights'] = 'License: ' + pkginfo['license']

        # archive.org requires case-insensitively unique identifiers, but
        # doesn't perform the mapping themselves. Thus, we do it here.
        identifier = self.db.get_item_identifier(identifier)

        for files in chunker(all_files, self.chunksize):
            try:
                res = self.ia.upload(identifier, files=files, metadata=metadata)
                file_status = zip(files, res)
                print_error = False
                for status in file_status:
                    f = status[0]
                    code = status[1].status_code
                    if code == 200:
                        filename = os.path.basename(f)
                        self.db.add_file(filename)
                    else:
                        print(f"Upload failed with status code '{code}' for directory '{directory}' and file: {f}", file=sys.stderr)
                        print_error = True

                if print_error:
                    print(directory)
                    returncode = 1
            except Exception as e:
                print(f"{identifier}: exception raised", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                print(directory)
                returncode = 1

        return returncode


    def main(self, pkg_dirs):
        """Upload all versions of each package"""
        exitcode = 0
        for pkg_dir in pkg_dirs:
            try:
                pkgname = os.path.basename(pkg_dir)
                identifier = self.clean_name('archlinux_pkg_' + pkgname)
                metadata = {
                    'collection': ['archlinuxarchive'],
                    'mediatype': 'software',
                    'publisher': 'Arch Linux',
                    'creator': 'Arch Linux',
                    'subject': ['archlinux', 'archlinux package'],
                }
                metadata['title'] = pkgname + " package archive from Arch Linux"
                metadata['subject'].append(pkgname)
                error = self.upload_pkg(identifier, pkgname, metadata, pkg_dir)
                if error:
                    exitcode = 1
            except Exception as e:
                print(f"{identifier}: exception raised", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                print(pkg_dir)
                exitcode = 1
        return exitcode

if __name__ == '__main__':
    sys.exit(ArchiveUploader().main(sys.argv[1:]))
