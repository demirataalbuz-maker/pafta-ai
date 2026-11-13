"""Rebuild harmless ELF/.NET curriculum inputs using installed compilers only.

No compiled input is executed. NuGet sources are disabled; missing SDK packs
fail instead of downloading dependencies. WSL compilation uses Linux /tmp.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'tracks/yara/fixtures/formats.json'


def build():
    records = {}
    def add(name, data, source, tool):
        records[name] = dict(base64=base64.b64encode(data).decode('ascii'),
                             sha256=hashlib.sha256(data).hexdigest(), source=source, tool=tool)
    distro = os.environ.get('PAFTA_WSL_DISTRO', 'kali-linux')
    gcc = subprocess.check_output(['wsl', '-d', distro, '--', 'gcc', '-dumpfullversion'], text=True).strip()
    variants = [('elf'+str(size), size, '.pafta', True, []) for size in (255,256,257)]
    variants += [('elf_other',256,'.other',True,[]), ('elf_write',256,'.pafta',False,[]),
                 ('elf32',256,'.pafta',True,['-m32']), ('elf_dyn',256,'.pafta',True,['-shared','-nostdlib'])]
    for name, size, section, readonly, flags in variants:
        source = f'{"const " if readonly else ""}unsigned char lab[{size}] __attribute__((section("{section}"))) = {{1}};\n'
        script = '''import base64, pathlib, subprocess, tempfile
with tempfile.TemporaryDirectory(prefix="pafta-yara-") as tmp:
 p=pathlib.Path(tmp)
 (p/"lab.c").write_bytes(base64.b64decode("SOURCE"))
 subprocess.run(["gcc",*FLAGS,"-fno-ident","-o",str(p/"lab.o"),str(p/"lab.c")],check=True)
 print(base64.b64encode((p/"lab.o").read_bytes()).decode())
'''.replace('SOURCE', base64.b64encode(source.encode()).decode()).replace('FLAGS', repr(flags if '-shared' in flags else ['-c']+flags))
        result = subprocess.run(['wsl', '-d', distro, '--', 'python3', '-c', script],
                                capture_output=True, text=True, check=True)
        add(name, base64.b64decode(result.stdout.strip()), source, f'gcc {gcc} {flags if "-shared" in flags else ["-c"]+flags} -fno-ident')
    sdk = subprocess.check_output(['dotnet', '--version'], text=True).strip()
    with tempfile.TemporaryDirectory(prefix='pafta-yara-dotnet-') as tmp:
        p = Path(tmp)
        (p/'empty-source').mkdir()
        (p/'NuGet.Config').write_text('<configuration><packageSources><clear /></packageSources></configuration>', encoding='utf-8')
        for name, major, assembly, namespace in (
            ('net1',1,'PaftaLab','Pafta.Sample'), ('net2',2,'PaftaLab','Pafta.Sample'),
            ('net3',3,'PaftaLab','Pafta.Sample'), ('net4',4,'PaftaLab','Pafta.Sample'),
            ('net_other',2,'OtherLab','Pafta.Sample'), ('net_namespace',2,'PaftaLab','Other.Sample')):
            folder = p/name
            folder.mkdir()
            source = f'namespace {namespace}; public sealed class Marker {{ public static int Value() => 7; }} internal sealed class Decoy {{}}\n'
            (folder/'Marker.cs').write_text(source, encoding='utf-8')
            project = f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>{assembly}</AssemblyName><AssemblyVersion>{major}.0.0.0</AssemblyVersion><Deterministic>true</Deterministic><DebugType>none</DebugType></PropertyGroup></Project>'
            (folder/'Lab.csproj').write_text(project, encoding='utf-8')
            subprocess.run(['dotnet','build',str(folder/'Lab.csproj'),'-c','Release','--nologo',
                            '--configfile',str(p/'NuGet.Config')], check=True, capture_output=True)
            add(name,(folder/f'bin/Release/net8.0/{assembly}.dll').read_bytes(),
                dict(csharp=source, csproj=project), f'.NET SDK {sdk}; Release; no external packages')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(f'{len(records)} compiler-produced inputs: tracks/yara/fixtures/formats.json')


if __name__ == '__main__':
    build()
