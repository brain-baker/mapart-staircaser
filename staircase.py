import sys
import os

CARPETS = {
    "minecraft:white_carpet", "minecraft:orange_carpet",
    "minecraft:magenta_carpet", "minecraft:light_blue_carpet",
    "minecraft:yellow_carpet", "minecraft:lime_carpet",
    "minecraft:pink_carpet", "minecraft:gray_carpet",
    "minecraft:light_gray_carpet", "minecraft:cyan_carpet",
    "minecraft:purple_carpet", "minecraft:blue_carpet",
    "minecraft:brown_carpet", "minecraft:green_carpet",
    "minecraft:red_carpet", "minecraft:black_carpet",
}

CARPET_DATA_TO_NAME = {
    0: "minecraft:white_carpet", 1: "minecraft:orange_carpet",
    2: "minecraft:magenta_carpet", 3: "minecraft:light_blue_carpet",
    4: "minecraft:yellow_carpet", 5: "minecraft:lime_carpet",
    6: "minecraft:pink_carpet", 7: "minecraft:gray_carpet",
    8: "minecraft:light_gray_carpet", 9: "minecraft:cyan_carpet",
    10: "minecraft:purple_carpet", 11: "minecraft:blue_carpet",
    12: "minecraft:brown_carpet", 13: "minecraft:green_carpet",
    14: "minecraft:red_carpet", 15: "minecraft:black_carpet",
}
CARPET_NAME_TO_DATA = {v: k for k, v in CARPET_DATA_TO_NAME.items()}

NH = 20


def get_step(x):
    return min(x // 7, 18)


def build_palette(carpets):
    pal = {"minecraft:air": 0, "minecraft:white_wool": 1}
    nid = 2
    for c in set(carpets.values()):
        if c not in pal:
            pal[c] = nid
            nid += 1
    return pal


def check_already_staircased(carpet_ys):
    """Returns True if carpets are at varying Y levels (already staircased)."""
    if not carpet_ys:
        return False
    y_values = set(carpet_ys.values())
    # If all carpets are on the same Y level, it's flat
    # If Y values span more than 1 level, it's already staircased
    return (max(y_values) - min(y_values)) > 1


# ========================= .nbt =========================

def read_nbt(path):
    import nbtlib
    f = nbtlib.load(path)
    size = [int(s) for s in f['size']]
    W, H, L = size[0], size[1], size[2]
    id2name = {i: str(e['Name']) for i, e in enumerate(f['palette'])}
    block_map = {}
    for b in f['blocks']:
        pos = tuple(int(p) for p in b['pos'])
        block_map[pos] = int(b['state'])
    carpets = {}
    carpet_ys = {}
    for x in range(W):
        for z in range(L):
            for y in range(H - 1, -1, -1):
                state = block_map.get((x, y, z))
                if state is not None and id2name.get(state, "") in CARPETS:
                    carpets[(x, z)] = id2name[state]
                    carpet_ys[(x, z)] = y
                    break
    return W, L, carpets, carpet_ys, f.get('DataVersion', nbtlib.Int(3465))


def save_nbt(path, W, L, carpets, pal, dv):
    from nbtlib import Int, List, Compound, String, File
    blocks = []
    wool_id = pal["minecraft:white_wool"]
    for (x, z), cname in carpets.items():
        step = get_step(x)
        blocks.append(Compound({
            'pos': List[Int]([Int(x), Int(step), Int(z)]),
            'state': Int(wool_id),
        }))
        blocks.append(Compound({
            'pos': List[Int]([Int(x), Int(step + 1), Int(z)]),
            'state': Int(pal[cname]),
        }))
    pal_list = [None] * len(pal)
    for name, idx in pal.items():
        pal_list[idx] = Compound({'Name': String(name)})
    File(Compound({
        'size': List[Int]([Int(W), Int(NH), Int(L)]),
        'palette': List[Compound](pal_list),
        'blocks': List[Compound](blocks),
        'DataVersion': dv,
        'entities': List[Compound](),
    }), gzipped=True).save(path)


# ========================= .schem =========================

def _decode_varints(raw, count):
    out, i = [], 0
    data = bytes(b & 0xFF for b in raw)
    while len(out) < count and i < len(data):
        val, shift = 0, 0
        while True:
            b = data[i]; i += 1
            val |= (b & 0x7F) << shift; shift += 7
            if not (b & 0x80): break
        out.append(val)
    return out


def _encode_varints(vals):
    out = []
    for v in vals:
        while True:
            b = v & 0x7F; v >>= 7
            if v: b |= 0x80
            out.append(b if b < 128 else b - 256)
            if not v: break
    return out


def read_schem(path):
    import nbtlib
    f = nbtlib.load(path)
    root = f.get('Schematic', f)
    W, H, L = int(root['Width']), int(root['Height']), int(root['Length'])
    if 'Blocks' in root and isinstance(root['Blocks'], nbtlib.Compound):
        pal_tag, bd_tag = root['Blocks']['Palette'], root['Blocks']['Data']
    else:
        pal_tag, bd_tag = root['Palette'], root['BlockData']
    id2name = {int(v): str(k) for k, v in pal_tag.items()}
    blocks = _decode_varints(bd_tag, W * H * L)
    carpets = {}
    carpet_ys = {}
    for x in range(W):
        for z in range(L):
            for y in range(H - 1, -1, -1):
                name = id2name.get(blocks[(y * L + z) * W + x], "minecraft:air")
                if name in CARPETS:
                    carpets[(x, z)] = name
                    carpet_ys[(x, z)] = y
                    break
    return W, L, carpets, carpet_ys, root.get('DataVersion', nbtlib.Int(3465))


def save_schem(path, W, L, carpets, pal, dv):
    from nbtlib import Short, Int, ByteArray, Compound, File
    arr = [0] * (W * NH * L)
    wool_id = pal["minecraft:white_wool"]
    for (x, z), cname in carpets.items():
        step = get_step(x)
        arr[(step * L + z) * W + x] = wool_id
        arr[((step + 1) * L + z) * W + x] = pal[cname]
    File({
        'Version': Int(2),
        'DataVersion': dv,
        'Width': Short(W),
        'Height': Short(NH),
        'Length': Short(L),
        'Palette': Compound({n: Int(i) for n, i in pal.items()}),
        'PaletteMax': Int(len(pal)),
        'BlockData': ByteArray(_encode_varints(arr)),
    }, gzipped=True).save(path)


# ========================= .litematic =========================

def read_litematic(path):
    from litemapy import Schematic
    schem = Schematic.load(path)
    reg = list(schem.regions.values())[0]
    xs, ys, zs = reg.xrange(), reg.yrange(), reg.zrange()
    min_x, min_z = min(xs), min(zs)
    W, L = len(xs), len(zs)
    carpets = {}
    carpet_ys = {}
    for x in xs:
        for z in zs:
            for y in reversed(list(ys)):
                block = reg.getblock(x, y, z)
                if block.blockid in CARPETS:
                    carpets[(x - min_x, z - min_z)] = block.blockid
                    carpet_ys[(x - min_x, z - min_z)] = y
                    break
    dv = getattr(schem, 'mc_data_version', 3465)
    return W, L, carpets, carpet_ys, dv


def save_litematic(path, W, L, carpets, pal, dv):
    from litemapy import Region, BlockState
    reg = Region(0, 0, 0, W, NH, L)
    wool = BlockState("minecraft:white_wool")
    for (x, z), cname in carpets.items():
        step = get_step(x)
        reg.setblock(x, step, z, wool)
        reg.setblock(x, step + 1, z, BlockState(cname))
    schem = reg.as_schematic(
        name="Staircased Map Art",
        author="staircase.py",
        description=""
    )
    schem.save(path)


# ========================= .schematic (legacy) =========================

def read_schematic(path):
    import nbtlib
    f = nbtlib.load(path)
    root = f.get('Schematic', f)
    W, H, L = int(root['Width']), int(root['Height']), int(root['Length'])
    blocks = [b & 0xFF for b in root['Blocks']]
    data = [b & 0xFF for b in root['Data']]
    carpets = {}
    carpet_ys = {}
    for x in range(W):
        for z in range(L):
            for y in range(H - 1, -1, -1):
                idx = (y * L + z) * W + x
                if blocks[idx] == 171:
                    carpets[(x, z)] = CARPET_DATA_TO_NAME.get(data[idx], "minecraft:white_carpet")
                    carpet_ys[(x, z)] = y
                    break
    return W, L, carpets, carpet_ys, None


def save_schematic(path, W, L, carpets, pal, dv):
    from nbtlib import Short, ByteArray, String, Compound, File
    blocks = [0] * (W * NH * L)
    data = [0] * (W * NH * L)
    for (x, z), cname in carpets.items():
        step = get_step(x)
        wool_idx = (step * L + z) * W + x
        blocks[wool_idx] = 35
        data[wool_idx] = 0
        carpet_idx = ((step + 1) * L + z) * W + x
        blocks[carpet_idx] = 171
        data[carpet_idx] = CARPET_NAME_TO_DATA.get(cname, 0)
    signed = lambda lst: [b if b < 128 else b - 256 for b in lst]
    File(Compound({
        'Width': Short(W),
        'Height': Short(NH),
        'Length': Short(L),
        'Materials': String('Alpha'),
        'Blocks': ByteArray(signed(blocks)),
        'Data': ByteArray(signed(data)),
    }), gzipped=True).save(path)


# ========================= Main =========================

READERS = {
    '.nbt': read_nbt,
    '.schem': read_schem,
    '.litematic': read_litematic,
    '.schematic': read_schematic,
}
SAVERS = {
    '.nbt': save_nbt,
    '.schem': save_schem,
    '.litematic': save_litematic,
    '.schematic': save_schematic,
}


def convert(inpath, outpath=None):
    base, ext = os.path.splitext(inpath)
    ext_l = ext.lower()
    if outpath is None:
        outpath = f"{base}(fixed){ext}"
    if ext_l not in READERS:
        raise ValueError(f"Unsupported: {ext}. Use: {', '.join(READERS)}")

    W, L, carpets, carpet_ys, dv = READERS[ext_l](inpath)

    if not carpets:
        raise ValueError("No carpets found!")

    if check_already_staircased(carpet_ys):
        raise ValueError("This file is already staircased! Carpets are at different Y levels. Only flat map art needs conversion.")

    pal = build_palette(carpets)
    SAVERS[ext_l](outpath, W, L, carpets, pal, dv)
    return outpath, len(carpets)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <input_file>")
        sys.exit(1)
    outpath, count = convert(sys.argv[1])
    print(f"Done! {count} carpets -> {outpath}")
