"""Exercise the built APT against native-style data-provider payloads."""
from pathlib import Path
import argparse
import json
import struct
import build


def verify(path, studio):
    build.dependencies(studio)
    from formats import AptFile, BigFile, Placement, Reader
    from apt_actions import Actions
    from apt_test_vm import NativeVM
    from apt_vm import Native, Object, Function

    apt = AptFile(BigFile(path))
    actions = Actions(apt).read_all()
    assert not actions.errors
    apt.validate_layout()
    # The generic decoder preserves raw bytes as Latin-1. FIFA's native text
    # path interprets the UTF-8 string operands emitted by our screen builder.
    def native_strings(code):
        for instruction in code:
            if isinstance(instruction.value, str):
                try:
                    instruction.value = instruction.value.encode('latin1').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            if instruction.body:
                native_strings(instruction.body)
    for code in actions.cache.values():
        native_strings(code)
    calls = []
    vm = None

    def native(name, owner, args):
        calls.append((name, owner, tuple(args)))
        if name == 'original.SetData':
            data = owner.get('m_objData')
            owner.get('txtTeam').set('text', data.get('TEAM_NAME'))
            owner.get('txtName').set('text', data.get('NAME'))
            owner.get('mcMiddle').set('_width', 230)
            vm.invoke(owner.get('__careerDrawCoachGraph'), owner)
        elif name == 'original.Publish':
            owner.set('m_objData', args[0].get('data')[0])
            vm.invoke(owner.get('SetData'), owner)
        elif name == 'createEmptyMovieClip':
            clip = Object({'_x': 0, '_y': 0, '_visible': True, 'drawing': []})
            owner.set(args[0], clip)
            return clip
        elif name == 'createTextField':
            owner.set(args[0], Object(dict(zip(('_x', '_y', '_width', '_height'), args[2:]))))
        elif name in ('setTextFormat', 'setNewTextFormat'):
            owner.set('format', args[0])
        elif name == 'clear':
            owner.set('drawing', [])
        elif name in ('lineStyle', 'beginFill', 'moveTo', 'lineTo', 'endFill'):
            owner.get('drawing').append((name, list(args)))

    class HeaderVM(NativeVM):
        def method(self, obj, name, args):
            if name == 'call' and isinstance(obj, (Function, Native)):
                return self.invoke(obj, args[0], args[1:])
            return super().method(obj, name, args)

    vm = HeaderVM(native)
    for code in actions.cache.values():
        if code[0].op == 136:
            vm.run(code, vm.global_, vm.global_)
    proto = vm.path('.'.join(build.PROTO))
    assert proto and proto.get(build.MARKER)
    methods = tuple(proto.get(name) for name in ('SetData', 'Publish', 'Shutdown'))
    for code in actions.cache.values():
        if code[0].op == 136:
            vm.run(code, vm.global_, vm.global_)
    assert methods == tuple(proto.get(name) for name in ('SetData', 'Publish', 'Shutdown'))
    for name in ('SetData', 'Publish', 'Shutdown'):
        proto.set(build.OLD + name, Native('original.' + name))
    vm.path('game').set('uif', Object({'UIFDataProviderList': Object(), 'UIFUtility': Object()}))
    vm.path('game.uif.UIFDataProviderList').set('CM_STATISTICS_DP', 900)
    vm.path('game.uif.UIFDataProviderList').set('CM_STANDINGS_DP', 700)
    vm.path('game.uif.UIFUtility').set('RegisterDataProvider', Native('RegisterDataProvider'))
    vm.path('game.uif.UIFUtility').set('UnregisterDataProvider', Native('UnregisterDataProvider'))

    data = Object({'ASSET_ID': 112893, 'TEAM_NAME': 'Inter Miami', 'NAME': 'Senhor Manager', 'IS_TOURNAMENTMODE': '0'})
    header = Object({'m_objData': data}, prototype=proto)
    for name, x, y, width, height in (
        ('mcHeaderLeft', 0, 0, 32, 79), ('mcMiddle', 32, 0, 378, 79),
        ('mcRight', 410, 0, 88, 79), ('mcCrest', 15, 5, 70, 70),
        ('txtTeam', 97, 5, 300, 30), ('txtName', 97, 37, 300, 30)):
        header.set(name, Object({'_x': x, '_y': y, '_width': width, '_height': height}))
    header.set('__careerCoachGraph', Object({'_visible': True}))
    for name in ('mcHeaderEfficiencyIcon', 'mcHeaderPrestigeIcon', 'mcHeaderMetricDivider'):
        header.set(name, Object())

    def invoke(name, *args):
        return vm.invoke(header.get(name), header, args)

    def publish(club, efficiency, prestige):
        rows = [Object({'ID': 'UNRELATED_TILE', 'PARAM': 'ignore'}),
                Object({'ID': 'CAREER_HEADER_EFFICIENCY', 'PARAM': '99%'})]
        rows.extend(Object({'ID': key, 'PARAM': value}) for key, value in (
            ('CAREER_HEADER_CLUB_ID', club), ('COACH_EFFICIENCY', efficiency),
            ('CAREER_HEADER_PRESTIGE', prestige)))
        invoke('Publish', Object({'data': rows}), 900)

    # Exercise the real legacy wrapper too. The stock API has two arguments,
    # as seen in the native CM_HUB_WIDGET_DP constructor/shutdown calls.
    invoke('InitComponents')
    assert [(args[0], args[1]) for name, _, args in calls if name == 'RegisterDataProvider'] == [(header, 700)]
    assert all(len(args) == 2 for name, _, args in calls if name == 'RegisterDataProvider')
    invoke('SetData')
    clip = header.get('__careerHeaderMetrics')
    assert clip.get('effValue').get('text') == '—'
    assert header.get('__careerCoachGraph').get('_visible') is False
    assert header.get('txtTeam').get('text') == 'Inter Miami'
    assert header.get('txtName').get('text') == 'Senhor Manager'
    invoke('SetData')
    registered = [args for name, _, args in calls if name == 'RegisterDataProvider']
    assert registered == [(header, 700), (header, 900)]
    publish(112893, '45%', '4,3/5')
    assert clip.get('effValue').get('text') == '45%'
    assert clip.get('prestigeValue').get('text') == '4,3/5'
    assert clip.get('effLabel').get('_y') == clip.get('prestigeLabel').get('_y') == 4
    assert clip.get('effValue').get('_y') == clip.get('prestigeValue').get('_y') == 0
    assert 'UNRELATED_TILE' not in header.get('__careerHeaderData').values
    # Native statistics can contain thousands of unrelated rows. Once our
    # trailing fields arrive, the header stops scanning the shared payload.
    unrelated = [Object({'ID': 'OTHER_' + str(index), 'PARAM': index}) for index in range(5000)]
    rows = [Object({'ID': key, 'PARAM': value}) for key, value in (
        ('CAREER_HEADER_CLUB_ID', 112893), ('COACH_EFFICIENCY', '45%'),
        ('CAREER_HEADER_PRESTIGE', '4,3/5'))]
    before = vm.steps
    invoke('Publish', Object({'data': unrelated + rows}), 900)
    assert vm.steps - before < 1500
    # Real career report: one win, two draws, one defeat. The native History
    # tile publishes 25% while points efficiency would be 41%. Share its field.
    publish(112893, '25%', '3,0/5')
    assert clip.get('effValue').get('text') == '25%'
    assert all(header.get(name).get('_height') == build.HEIGHT for name in ('mcHeaderLeft', 'mcMiddle', 'mcRight'))
    assert header.get('mcCrest').get('_y') == 5 + (build.HEIGHT - 79) / 2
    # A crest loaded asynchronously must stay centered even while its loader
    # reports height zero. This reproduces the observed downward displacement.
    header.get('mcCrest').set('_height', 0)
    invoke('__careerDrawCoachGraph')
    assert header.get('mcCrest').get('_y') == 5 + (build.HEIGHT - 79) / 2
    assert clip.get('_x') + build.ROW_WIDTH < header.get('mcRight').get('_x')
    snapshot = {'texts': {name: dict(clip.get(name).values) for name in ('effLabel', 'effValue', 'prestigeLabel', 'prestigeValue')},
                'drawing': clip.get('drawing'), 'x': clip.get('_x'), 'y': clip.get('_y'),
                'right_x': header.get('mcRight').get('_x')}
    for field in snapshot['texts'].values():
        field['format'] = dict(field['format'].values)
    publish(1043, '100%', '5,0/5')
    assert clip.get('effValue').get('text') == '—'
    invoke('Publish', Object({'data': [Object({'ASSET_ID': 1043, 'TEAM_NAME': 'Flamengo', 'NAME': 'Outro Manager', 'IS_TOURNAMENTMODE': '0'})]}), 901)
    assert header.get('__careerHeaderData') is None
    assert header.get('txtTeam').get('text') == 'Flamengo'
    publish(1043, '', '')
    assert clip.get('effValue').get('text') == clip.get('prestigeValue').get('text') == '—'
    publish(1043, '0%', '3,0/5')
    assert clip.get('effValue').get('text') == '0%'
    header.get('m_objData').set('IS_TOURNAMENTMODE', '1')
    invoke('SetData')
    assert clip.get('_visible') is False and header.get('mcMiddle').get('_height') == 79
    assert all(header.get(name).get('_visible') is False for name in ('mcHeaderEfficiencyIcon', 'mcHeaderPrestigeIcon', 'mcHeaderMetricDivider'))
    invoke('Shutdown'); invoke('Shutdown')
    assert len([name for name, _, _ in calls if name == 'UnregisterDataProvider']) == 1
    assert header.get('__careerHeaderData') is None

    # Native relocation dereferences even anonymous Function2 name/parameter pointers.
    for code in actions.cache.values():
        for instruction in code:
            if instruction.op != 142:
                continue
            reader = Reader(apt.data, instruction.offset + 1, 8)
            name_pointer = reader.ptr()
            assert 0 < name_pointer < len(apt.data)
            reader.string(name_pointer)
            reader.pos = (reader.pos + 3) // 4 * 4
            count = reader.i(); reader.read('h'); reader.read('H')
            parameters = reader.ptr()
            assert 0 < parameters and parameters + count * 16 <= len(apt.data)
            assert all(item.op != 0 for item in instruction.body)
    component = next(character for character in apt.characters.values()
                     if character.type == 5 and any(isinstance(p, Placement) and p.name == 'txtTeam' for frame in character.frames for p in frame))
    left = next(p for p in component.frames[0] if isinstance(p, Placement) and p.name == 'mcHeaderLeft')
    assert apt.characters[left.character].type == 5
    for name in ('mcHeaderEfficiencyIcon', 'mcHeaderPrestigeIcon', 'mcHeaderMetricDivider'):
        placement = next(p for p in component.frames[0] if isinstance(p, Placement) and p.name == name)
        symbol = apt.characters[placement.character]
        assert symbol.type == 5
        child = next(p for p in symbol.frames[0] if isinstance(p, Placement))
        assert apt.characters[child.character].type == 1
        geo = apt.big.entries[str(child.character + 1)].data
        declared_triangles = struct.unpack_from('<I', geo, 88)[0]
        assert declared_triangles == (len(geo) - 96) // 96, 'Native triangle count truncates the icon in FIFA'
        assert declared_triangles > 0
        vertices = [struct.unpack_from('<2f', geo, offset) for offset in range(96, len(geo), 32)]
        assert len(vertices) == declared_triangles * 3
        assert max(x for x, _ in vertices) > min(x for x, _ in vertices)
        assert max(y for _, y in vertices) > min(y for _, y in vertices)
    assert not vm.errors
    output = Path(path).parent / 'verification.json'
    output.write_text(json.dumps({'passed': True, 'steps': vm.steps, 'preview': snapshot}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS header APT: native ID/PARAM payloads, repeated lifecycle, club changes, empty values, tournament and native relocation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--studio', type=Path, required=True)
    args = parser.parse_args()
    verify(args.input, args.studio)
