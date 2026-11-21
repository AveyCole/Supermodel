"""Build Sequencer Directions from verified Supermodel 3.06 release inputs."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

project = Path(__file__).resolve().parent
repo = Path(sys.argv.pop(1))
stock = Path(sys.argv.pop(1))
reference = Path(sys.argv.pop(1))
capture = Path(sys.argv.pop(1))
output = Path(sys.argv.pop(1))
output.mkdir(parents=True, exist_ok=True)

def run(tool, *arguments):
    return subprocess.check_output(['m68k-linux-gnu-' + tool, *map(str, arguments)], text=True)

def install(meta, native, runtime):
    origin, reservation = 0x46938000, 0x1000
    offset = origin - 0x46700000
    assert meta['sha256'] in ('45914e449cd4ef75d56c1f083fcb7b77efa7fae749731547fd5bf77929cd77f5', 'f73d11874910a70e1ca36e868c0c7347ecba4062656b5547e2eb52d0a97a60b3', '91e2003f49f4bd5386f2f551cd5ac2330f912d63f68d3702fa4b62204f576da4', 'bec4ce45aca72d10ba263dc2f4e58f9104873fb5a58199e308fe742bbe4d701f')
    assert not any(runtime[offset:offset + reservation])
    assert not any(a['address'] < origin+reservation and origin < a['address']+a['bytes']
                   for a in meta['clean_layout']['segments'])
    for key,item in meta.items():
        if isinstance(item,dict):
            for start, end in [('code','code_end'),('bss','bss_end')]:
                a=item.get(start)
                if isinstance(a,int):
                    b=item.get(end,a+item.get(start+'_bytes',1))
                    assert not (a < origin+reservation and origin < b), key

    def jmp(addr):
        return b'\x4e\xf9'+struct.pack('>I',addr)

    sites = {
        'midi12_direction_prepare_hook': (0x400550da, '4ef940184df8'),
        'midi12_direction_advance_hook': (0x40055344, '4ef9468f7c044e71'),
        'private_direction_keys': (0x40077720, '4ef9468b8e984e71'),
        'midi12_direction_loop_hook': (0x400558b6, '3212420617810800'),
        'private_direction_start': (0x4005502e, '424042b940a78840'),
        'private_direction_transport': (0x40054c8a, '4ef9468f8348'),
    }
    base=0x40000400
    for address, expected in sites.values():
        assert native[address-base:address-base+len(expected)//2].hex()==expected
    assert native[0x40055360-base:0x4005536c-base].hex()=='20452f024e90588f72015282'

    previous={name:int(encoded[4:12],16) for name, (_, encoded) in sites.items()}
    page=meta['page_length']['symbols']
    cal=meta['control_all_latch']['symbols']
    aliases=dict(pt_length=page['pt_length'], pl_step_hook=previous['midi12_direction_advance_hook'],
                direction_original_keys=previous['private_direction_keys'],
                direction_original_transport=previous['private_direction_transport'],
                fx_notice=meta['fx_menu']['symbols']['fx_notice'])
    for name in ('clean','second','armed'):
        aliases['control_track_'+name]=cal[name]
    aliases.update(control_back_clean=cal['bc'],control_back_armed=cal['ba'])

    port = project/'machines/sequencer_directions'
    linker=output/'direction.ld'
    linker.write_text(''.join(f'{name} = {addr:#x};\n' for name,addr in aliases.items())+
        f'SECTIONS {{ .direction {origin:#x} : {{ *(.text*) *(.rodata*) *(.data*) *(.bss*) . = ALIGN(4); }} }}\n')
    obj=[]
    for source in ('play_direction.c','play_direction_hooks.S','shortcut.c','shortcut.S'):
        path=output/(source+'.o')
        run('gcc','-mcpu=54418','-Os','-ffreestanding','-fno-builtin','-fno-pic',
            '-fno-stack-protector','-fno-tree-loop-distribute-patterns','-Wall','-Wextra','-Werror',
             '-c',port/source,'-o',path)
        obj.append(path)
    elf=output/'direction.elf'
    raw=output/'direction.bin'
    run('ld','-T',linker,'-e','private_direction_keys','-o',elf,*obj)
    run('objcopy','-O','binary',elf,raw)
    symbols={v[2]:int(v[0],16) for line in run('nm',elf).splitlines() if len(v:=line.split())==3}
    payload=bytearray(raw.read_bytes())
    assert len(payload)<=reservation
    pos=symbols['midi12_direction_scheduler']-origin
    assert payload[pos:pos+4]==bytes(4)
    struct.pack_into('>I',payload,pos,previous['midi12_direction_prepare_hook'])
    runtime[offset:offset+len(payload)]=payload
    for name,(site,expected) in sites.items():
        at=site-base
        native[at:at+len(expected)//2]=jmp(symbols[name])+b'\x4e\x71'*((len(expected)//2-6)//2)
    meta['sequencer_directions']=dict(origin=origin, bytes=len(payload), symbols=symbols,
        source=meta['sha256'], hardware_tested=False)

tool=repo/'tools/rebuild300_pack.py'
contents=tool.read_text(encoding='utf-8').replace('H:/CREATURE-source/retrosyn-integration/build/m68k-toolchain/pkg/bin/m68k-elf-', 'm68k-linux-gnu-').replace('cross+tool+\x27.exe\x27'.replace(chr(92)+'x27', chr(39)), 'cross+tool')
anchor="    spans=sparse(0x4019b590,native[boundary:])"
assert contents.count(anchor)==1
contents=contents.replace(anchor,"    install(meta,image,runtime)\n"+anchor)
sys.path.insert(0,str(tool.parent))
sys.argv=[str(tool),'--cycles',str(stock),'--reference',str(reference),'--capture',str(capture),
          '--output',str(output),'--release','3.06','--compression-history',
          '--compression-candidates','16','--compression-window','16777216','--compression-min-match','3']
exec(compile(contents,tool,'exec'),dict(__file__=str(tool),__name__='__main__',install=install))



