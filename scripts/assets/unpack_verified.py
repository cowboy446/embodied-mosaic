"""Verify an asset ZIP, extract to a new directory, and inventory USD entrypoints.
All members retain their paths; relative links are accepted only within the output.
"""
import argparse,hashlib,json,os,shutil,stat,zipfile
from pathlib import Path,PurePosixPath


def checked_name(name):
    p=PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
        raise ValueError(f'unsafe archive member: {name}')
    return p


def extract(archive,destination):
    dest=Path(destination).resolve()
    if dest.exists():raise FileExistsError(dest)
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist();seen=set();links=[]
        for info in infos:
            name=str(checked_name(info.filename))
            if name in seen:raise ValueError(f'duplicate archive member: {name}')
            seen.add(name)
        dest.parent.mkdir(parents=True,exist_ok=True)
        if sum(i.file_size for i in infos)>shutil.disk_usage(dest.parent).free:
            raise RuntimeError('insufficient extraction space')
        dest.mkdir()
        for info in infos:
            target=dest/str(checked_name(info.filename));mode=info.external_attr>>16
            if stat.S_ISLNK(mode):links.append((target,z.read(info).decode('utf-8')));continue
            if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as source,target.open('xb') as sink:shutil.copyfileobj(source,sink,1024*1024)
        # Create links after regular files, so no write follows an archive link.
        for target,value in links:
            if os.path.isabs(value) or '\\' in value:raise ValueError('unsafe symlink target')
            resolved=(target.parent/value).resolve()
            if not resolved.is_relative_to(dest):raise ValueError('symlink escapes output')
            target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(value)
        for target,_ in links:
            if not target.resolve().is_relative_to(dest):raise ValueError('chained symlink escapes output')
        return {'members':len(infos),'uncompressed_bytes':sum(i.file_size for i in infos),'symlinks':len(links)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    archive=Path(a.archive);h=hashlib.sha256()
    with archive.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    if h.hexdigest()!=a.sha256:raise RuntimeError('SHA256 mismatch')
    final=Path(a.output);partial=final.with_name(final.name+'.extracting')
    if final.exists():raise FileExistsError(final)
    report=extract(archive,partial)
    report.update(archive=str(archive),sha256=h.hexdigest(),license='CC-BY-NC-SA-4.0',
                  scene_entrypoints=[str(f.relative_to(partial)) for f in partial.rglob('start_result*.usd')],
                  metadata_files=[str(f.relative_to(partial)) for f in partial.rglob('metadata.json')],
                  scope='archive integrity and inventory; USD/material/physics compatibility not yet validated')
    (partial/'extraction-manifest.json').write_text(json.dumps(report,indent=2));partial.rename(final)
    print(json.dumps({'output':str(final),'scene_entrypoints':len(report['scene_entrypoints']),**{k:report[k] for k in ['members','uncompressed_bytes','symlinks']}}))
if __name__=='__main__':main()
